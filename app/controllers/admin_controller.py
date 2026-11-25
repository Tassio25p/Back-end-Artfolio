from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc

from app.database import get_db
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.models.postagem_model import Postagem
from app.models.denuncia_model import Denuncia
from app.models.denuncia_chat_model import DenunciaChat
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.models.log_auditoria_model import LogAuditoria
from app.models.categoria_model import Categoria

from app.schemas.admin_schema import (
    AdminMetricasResposta,
    JulgarObraRequisicao,
    SancaoUsuarioRequisicao,
    AtualizarDenunciaRequisicao,
    DesafioCriarRequisicao,
    DesafioAtualizarRequisicao,
    DenunciaChatResposta,
    AuditoriaChatResposta,
    MensagemAuditoriaResposta,
    ObraQuarentenaResposta,
    LogAuditoriaResposta,
    UsuarioSinalizadoResposta,
)

router = APIRouter(prefix="/admin", tags=["Administração / Moderação"])


def exigir_moderador_ou_admin(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
) -> Usuario:
    """
    Dependência de segurança que valida se o usuário autenticado é moderador ou admin.
    Garante que usuario_atual.papel in ['admin', 'moderador'].
    """
    papel = getattr(usuario_atual, "papel", None) or getattr(usuario_atual, "tipo_conta", None)
    if not papel or str(papel).lower() not in ["admin", "moderador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito. Apenas administradores e moderadores podem acessar este recurso.",
        )
    return usuario_atual


def _coletar_ids_usuarios_sinalizados(db: Session) -> Set[int]:
    """
    Retorna o conjunto de IDs de usuários (excluindo admins e moderadores) que possuem
    algum motivo real de sinalização:
    1. Denúncias de chat recebidas
    2. Denúncias em suas obras publicadas
    3. Obras em quarentena ou rejeitadas
    4. Sanções disciplinares (suspenso, banido ou advertido em log)
    """
    ids: Set[int] = set()

    # 1. Denúncias de chat
    for (uid,) in db.query(DenunciaChat.denunciado_id).distinct().all():
        if uid:
            ids.add(int(uid))

    # 2. Denúncias de obras
    try:
        rows_den_obra = (
            db.query(Postagem.idUsuario)
            .join(Denuncia, Denuncia.idPostagem == Postagem.id)
            .distinct()
            .all()
        )
        for (uid,) in rows_den_obra:
            if uid:
                ids.add(int(uid))
    except Exception:
        pass

    # 3. Obras em quarentena ou rejeitadas
    rows_obras = (
        db.query(Postagem.idUsuario)
        .filter(Postagem.status.in_(["quarentena", "rejeitada"]))
        .distinct()
        .all()
    )
    for (uid,) in rows_obras:
        if uid:
            ids.add(int(uid))

    # 4. Usuários suspensos ou inativos/banidos
    rows_status = (
        db.query(Usuario.id)
        .filter(or_(Usuario.ativo == False, Usuario.suspenso_ate != None))
        .all()
    )
    for (uid,) in rows_status:
        if uid:
            ids.add(int(uid))

    # 5. Usuários que receberam sanções nos logs de auditoria
    rows_logs = (
        db.query(LogAuditoria.alvo_id)
        .filter(LogAuditoria.alvo_tipo == "usuario")
        .distinct()
        .all()
    )
    for (uid,) in rows_logs:
        if uid:
            ids.add(int(uid))

    if not ids:
        return set()

    # Filtrar para remover contas administrativas/moderadores da lista de infratores
    usuarios_validos = (
        db.query(Usuario.id, Usuario.tipo_conta)
        .filter(Usuario.id.in_(ids))
        .all()
    )
    return {
        u_id
        for u_id, t_conta in usuarios_validos
        if str(t_conta or "artista").lower() not in ["admin", "moderador"]
    }


def _serializar_desafio(d: Categoria) -> dict:
    agora = datetime.now(timezone.utc)
    prazo = getattr(d, "prazo_dias", 7) or 7
    inicio = d.data_inicio_desafio
    fim = getattr(d, "data_fim_desafio", None)

    if inicio and inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    if fim and fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)

    if inicio and not fim:
        fim = inicio + timedelta(days=prazo)

    dias_restantes = None
    if d.desafio_ativo and fim:
        delta = fim - agora
        dias_restantes = max(0, int(delta.total_seconds() // 86400) + (1 if delta.total_seconds() % 86400 > 0 else 0))

    return {
        "id": d.id,
        "nomeCategoria": d.nomeCategoria,
        "is_desafio": True,
        "desafio_ativo": bool(d.desafio_ativo),
        "prazo_dias": prazo,
        "data_inicio_desafio": inicio.isoformat() if inicio else None,
        "data_fim_desafio": fim.isoformat() if fim else None,
        "dias_restantes": dias_restantes,
    }


# ======================================================================
# A) Métricas do Topo
# ======================================================================
@router.get(
    "/metricas",
    response_model=AdminMetricasResposta,
    summary="Obter métricas consolidadas em tempo real do painel administrativo",
)
def obter_metricas(
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna a contagem em tempo real:
    - obras_pendentes: artes com status='quarentena' ou 'pendente'
    - denuncias_abertas: denúncias de chat com status='pendente'
    - usuarios_sinalizados: usuários (não-admins) com denúncias ou infrações reais
    - logs_recentes: total de ações de moderação registradas
    """
    obras_pendentes = (
        db.query(Postagem)
        .filter(
            Postagem.deletado == False,
            Postagem.status.in_(["quarentena", "pendente"]),
        )
        .count()
    )

    denuncias_abertas = (
        db.query(DenunciaChat)
        .filter(DenunciaChat.status == "pendente")
        .count()
    )

    ids_sinalizados = _coletar_ids_usuarios_sinalizados(db)
    usuarios_sinalizados = len(ids_sinalizados)

    logs_recentes = db.query(LogAuditoria).count()

    return AdminMetricasResposta(
        obras_pendentes=obras_pendentes,
        denuncias_abertas=denuncias_abertas,
        usuarios_sinalizados=usuarios_sinalizados,
        logs_recentes=logs_recentes,
    )


# ======================================================================
# B) Denúncias de Chat e Auditoria
# ======================================================================
@router.get(
    "/denuncias",
    response_model=List[DenunciaChatResposta],
    summary="Listar denúncias de chat para moderação",
)
def listar_denuncias_chat(
    status_filtro: Optional[str] = Query(None, alias="status"),
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todas as denúncias de chat, trazendo dados do denunciante, denunciado e motivo.
    """
    query = db.query(DenunciaChat)
    if status_filtro:
        query = query.filter(DenunciaChat.status == status_filtro.lower())
    denuncias = query.order_by(
        desc(DenunciaChat.status == "pendente"),
        DenunciaChat.criado_em.desc(),
    ).all()

    resposta = []
    for d in denuncias:
        resposta.append(
            DenunciaChatResposta(
                id=d.id,
                denunciante_id=d.denunciante_id,
                denunciante_nome=d.denunciante.nome if d.denunciante else f"Usuário #{d.denunciante_id}",
                denunciante_email=d.denunciante.email if d.denunciante else None,
                denunciado_id=d.denunciado_id,
                denunciado_nome=d.denunciado.nome if d.denunciado else f"Usuário #{d.denunciado_id}",
                denunciado_email=d.denunciado.email if d.denunciado else None,
                conversa_id=d.conversa_id,
                motivo=d.motivo,
                descricao=d.descricao,
                status=d.status,
                nota_moderador=d.nota_moderador,
                criado_em=d.criado_em,
            )
        )
    return resposta


@router.get(
    "/denuncias/{denuncia_id}/auditoria-chat",
    response_model=AuditoriaChatResposta,
    summary="Auditar histórico completo de mensagens de uma conversa denunciada",
)
def auditar_chat(
    denuncia_id: int,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna a conversa COMPLETA associada à denúncia.
    Traz inclusive mensagens deletadas pelo usuário com a flag foi_apagada=True
    e mensagens alteradas com a flag foi_editada=True.
    """
    denuncia = db.query(DenunciaChat).filter(DenunciaChat.id == denuncia_id).first()
    if not denuncia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Denúncia não encontrada.",
        )

    mensagens = (
        db.query(Mensagem)
        .filter(Mensagem.idConversa == denuncia.conversa_id)
        .order_by(Mensagem.dataEnvio.asc())
        .all()
    )

    mensagens_resposta: List[MensagemAuditoriaResposta] = []
    for m in mensagens:
        apagada = bool(m.deletado or m.deletado_em is not None or m.dataDelecao is not None)
        apagado_em = m.deletado_em or m.dataDelecao
        editada = bool(m.editado_em is not None)

        mensagens_resposta.append(
            MensagemAuditoriaResposta(
                id=m.id,
                idRemetente=m.idRemetente,
                nomeRemetente=m.remetente.nome if m.remetente else f"Usuário #{m.idRemetente}",
                fotoPerfilRemetente=m.remetente.fotoPerfil if m.remetente else None,
                conteudo=m.conteudo,
                arquivoUrl=m.arquivoUrl,
                dataEnvio=m.dataEnvio,
                foi_apagada=apagada,
                apagado_em=apagado_em,
                foi_editada=editada,
                editado_em=m.editado_em,
            )
        )

    return AuditoriaChatResposta(
        denuncia_id=denuncia.id,
        conversa_id=denuncia.conversa_id,
        denunciante_id=denuncia.denunciante_id,
        denunciado_id=denuncia.denunciado_id,
        motivo=denuncia.motivo,
        descricao=denuncia.descricao,
        mensagens=mensagens_resposta,
    )


@router.patch(
    "/denuncias/{denuncia_id}",
    response_model=DenunciaChatResposta,
    summary="Atualizar status da denúncia com nota do moderador",
)
def atualizar_denuncia(
    denuncia_id: int,
    dados: AtualizarDenunciaRequisicao,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Atualiza status para 'resolvida' ou 'descartada', gravando nota_moderador e log de auditoria.
    """
    denuncia = db.query(DenunciaChat).filter(DenunciaChat.id == denuncia_id).first()
    if not denuncia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Denúncia não encontrada.",
        )

    novo_status = dados.status.lower()
    if novo_status not in ["resolvida", "descartada", "em_analise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido. Use 'resolvida' ou 'descartada'.",
        )

    denuncia.status = novo_status
    denuncia.nota_moderador = dados.nota_moderador
    denuncia.moderador_id = moderador.id
    denuncia.resolvido_em = datetime.now(timezone.utc)

    log = LogAuditoria(
        moderador_id=moderador.id,
        acao=f"denuncia_{novo_status}",
        alvo_tipo="denuncia_chat",
        alvo_id=denuncia.id,
        detalhes=f"Denúncia #{denuncia.id} marcada como '{novo_status}'. Nota: {dados.nota_moderador or 'Nenhuma'}",
    )
    db.add(log)
    db.commit()
    db.refresh(denuncia)

    return DenunciaChatResposta(
        id=denuncia.id,
        denunciante_id=denuncia.denunciante_id,
        denunciante_nome=denuncia.denunciante.nome if denuncia.denunciante else None,
        denunciante_email=denuncia.denunciante.email if denuncia.denunciante else None,
        denunciado_id=denuncia.denunciado_id,
        denunciado_nome=denuncia.denunciado.nome if denuncia.denunciado else None,
        denunciado_email=denuncia.denunciado.email if denuncia.denunciado else None,
        conversa_id=denuncia.conversa_id,
        motivo=denuncia.motivo,
        descricao=denuncia.descricao,
        status=denuncia.status,
        nota_moderador=denuncia.nota_moderador,
        criado_em=denuncia.criado_em,
    )


# ======================================================================
# C) Quarentena de Obras
# ======================================================================
@router.get(
    "/obras/quarentena",
    response_model=List[ObraQuarentenaResposta],
    summary="Listar obras em quarentena ou pendentes de análise",
)
def listar_obras_quarentena(
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Lista postagens com status='quarentena' ou 'pendente'.
    """
    obras = (
        db.query(Postagem)
        .filter(
            Postagem.deletado == False,
            Postagem.status.in_(["quarentena", "pendente"]),
        )
        .order_by(Postagem.dataPostagem.desc())
        .all()
    )

    resposta: List[ObraQuarentenaResposta] = []
    for o in obras:
        cats = [c.nomeCategoria for c in o.categorias] if o.categorias else []
        resposta.append(
            ObraQuarentenaResposta(
                id=o.id,
                idUsuario=o.idUsuario,
                artista_nome=o.usuario.nome if o.usuario else f"Artista #{o.idUsuario}",
                artista_email=o.usuario.email if o.usuario else None,
                artista_foto=o.usuario.fotoPerfil if o.usuario else None,
                legenda=o.legenda,
                arquivoUrl=o.arquivoUrl,
                arquivos=o.arquivos,
                status=o.status,
                dataPostagem=o.dataPostagem,
                categorias=cats,
            )
        )
    return resposta


@router.patch(
    "/obras/{obra_id}/julgar",
    summary="Julgar obra em quarentena (aprovar ou rejeitar)",
)
def julgar_obra(
    obra_id: int,
    dados: JulgarObraRequisicao,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Aprova ou rejeita uma obra em quarentena.
    """
    obra = db.query(Postagem).filter(Postagem.id == obra_id).first()
    if not obra:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obra não encontrada.",
        )

    acao = dados.acao.lower().strip()
    if acao not in ["aprovar", "rejeitar"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ação inválida. Use 'aprovar' ou 'rejeitar'.",
        )

    if acao == "aprovar":
        obra.status = "publicada"
        obra.deletado = False

        notif = Notificacao(
            idUsuario=obra.idUsuario,
            tipo="sistema",
            titulo="Sua obra foi aprovada!",
            mensagem="Parabéns! Sua publicação foi revisada pela equipe de moderação e agora está pública no feed do Artfolio.",
            idPostagem=obra.id,
        )
        db.add(notif)

        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="obra_aprovada",
            alvo_tipo="obra",
            alvo_id=obra.id,
            detalhes=f"Obra #{obra.id} aprovada e publicada pelo moderador {moderador.nome}.",
        )
        db.add(log)

    else:
        motivo = dados.motivo.strip() if dados.motivo else "Violação das diretrizes da comunidade."
        obra.status = "rejeitada"
        obra.deletado = True
        obra.dataDelecao = datetime.now(timezone.utc)

        notif = Notificacao(
            idUsuario=obra.idUsuario,
            tipo="sistema",
            titulo="Sua obra foi rejeitada pela moderação",
            mensagem=f"Sua publicação foi removida por não atender às diretrizes da plataforma. Motivo: {motivo}",
            idPostagem=obra.id,
        )
        db.add(notif)

        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="obra_rejeitada",
            alvo_tipo="obra",
            alvo_id=obra.id,
            detalhes=f"Obra #{obra.id} rejeitada. Motivo: {motivo}",
        )
        db.add(log)

    db.commit()
    db.refresh(obra)

    return {
        "mensagem": f"Obra #{obra.id} {acao}da com sucesso.",
        "obra_id": obra.id,
        "status": obra.status,
    }


# ======================================================================
# D) Punição / Sanção de Usuários Infratores
# ======================================================================
@router.patch(
    "/usuarios/{usuario_id}/sancao",
    summary="Aplicar sanção disciplinar a um usuário (advertir, suspender, banir)",
)
def aplicar_sancao_usuario(
    usuario_id: int,
    dados: SancaoUsuarioRequisicao,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Aplica uma sanção formal ao usuário infrator.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    alvo_papel = getattr(usuario, "papel", None) or getattr(usuario, "tipo_conta", None)
    if alvo_papel and str(alvo_papel).lower() in ["admin", "moderador"] and usuario.id != moderador.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é permitido aplicar sanções administrativas a membros da equipe de moderação.",
        )

    acao = dados.acao.lower().strip()
    motivo = dados.motivo.strip() if dados.motivo else "Violação dos Termos de Uso e Diretrizes da Comunidade"

    if acao == "advertir":
        notif = Notificacao(
            idUsuario=usuario.id,
            tipo="sistema",
            titulo="Advertência Formal da Moderação",
            mensagem=f"Você recebeu uma advertência formal da equipe de moderação. Motivo: {motivo}. Reincidências resultarão em suspensão ou banimento.",
        )
        db.add(notif)

        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="usuario_advertido",
            alvo_tipo="usuario",
            alvo_id=usuario.id,
            detalhes=f"Advertência formal enviada a {usuario.nome} (ID #{usuario.id}). Motivo: {motivo}",
        )
        db.add(log)

    elif acao == "suspender":
        dias = dados.dias_suspensao if (dados.dias_suspensao and dados.dias_suspensao > 0) else 7
        data_fim = datetime.now(timezone.utc) + timedelta(days=dias)
        usuario.suspenso_ate = data_fim

        notif = Notificacao(
            idUsuario=usuario.id,
            tipo="sistema",
            titulo="Conta Suspensa Temporariamente",
            mensagem=f"Sua conta foi suspensa por {dias} dias devido a infrações recorrentes. Motivo: {motivo}. Acesso liberado após {data_fim.strftime('%d/%m/%Y')}.",
        )
        db.add(notif)

        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="usuario_suspenso",
            alvo_tipo="usuario",
            alvo_id=usuario.id,
            detalhes=f"Usuário {usuario.nome} (ID #{usuario.id}) suspenso por {dias} dias até {data_fim.strftime('%d/%m/%Y')}. Motivo: {motivo}",
        )
        db.add(log)

    elif acao == "banir":
        usuario.ativo = False
        usuario.deletado = True
        usuario.dataDelecao = datetime.now(timezone.utc)

        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="usuario_banido",
            alvo_tipo="usuario",
            alvo_id=usuario.id,
            detalhes=f"Usuário {usuario.nome} (ID #{usuario.id}) BANIDO permanentemente da plataforma. Motivo: {motivo}",
        )
        db.add(log)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ação inválida. Use 'advertir', 'suspender' ou 'banir'.",
        )

    db.commit()
    db.refresh(usuario)

    return {
        "mensagem": f"Sanção '{acao}' aplicada com sucesso ao usuário #{usuario.id}.",
        "usuario_id": usuario.id,
        "acao": acao,
        "ativo": usuario.ativo,
        "suspenso_ate": usuario.suspenso_ate,
    }


# ======================================================================
# E) Logs de Auditoria e Usuários Sinalizados (Com Explicação Detalhada)
# ======================================================================
@router.get(
    "/logs",
    response_model=List[LogAuditoriaResposta],
    summary="Listar histórico de logs de auditoria da moderação",
)
def listar_logs_auditoria(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna os logs de auditoria em ordem decrescente de criação.
    """
    logs = (
        db.query(LogAuditoria)
        .order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    resposta: List[LogAuditoriaResposta] = []
    for l in logs:
        resposta.append(
            LogAuditoriaResposta(
                id=l.id,
                moderador_id=l.moderador_id,
                moderador_nome=l.moderador.nome if l.moderador else f"Moderador #{l.moderador_id}",
                acao=l.acao,
                alvo_tipo=l.alvo_tipo,
                alvo_id=l.alvo_id,
                detalhes=l.detalhes,
                criado_em=l.criado_em,
            )
        )
    return resposta


@router.get(
    "/usuarios/sinalizados",
    response_model=List[UsuarioSinalizadoResposta],
    summary="Listar usuários sinalizados com explicação detalhada dos motivos",
)
def listar_usuarios_sinalizados(
    q: Optional[str] = Query(None, description="Busca opcional por nome ou e-mail de usuário"),
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna apenas os usuários que realmente possuem sinalizações (denúncias de chat,
    denúncias de obras, obras retidas/rejeitadas ou sanções disciplinares), excluindo
    contas de admin/moderador, e detalha exatamente o porquê de cada usuário estar sinalizado.
    Se o parâmetro 'q' for informado, permite pesquisar usuários pelo nome ou e-mail.
    """
    if q and q.strip():
        termo = f"%{q.strip()}%"
        usuarios_alvo = (
            db.query(Usuario)
            .filter(
                Usuario.tipo_conta.notin_(["admin", "moderador"]),
                or_(
                    Usuario.nome.ilike(termo),
                    Usuario.email.ilike(termo),
                ),
            )
            .order_by(Usuario.id.desc())
            .limit(20)
            .all()
        )
    else:
        ids_sinalizados = _coletar_ids_usuarios_sinalizados(db)
        if not ids_sinalizados:
            return []
        usuarios_alvo = (
            db.query(Usuario)
            .filter(Usuario.id.in_(ids_sinalizados))
            .all()
        )

    resposta: List[UsuarioSinalizadoResposta] = []
    agora_naive = datetime.utcnow()

    for u in usuarios_alvo:
        motivos: List[str] = []

        # 1. Denúncias de Chat contra o usuário
        denuncias_chat = (
            db.query(DenunciaChat)
            .filter(DenunciaChat.denunciado_id == u.id)
            .order_by(DenunciaChat.criado_em.desc())
            .all()
        )
        for dc in denuncias_chat:
            status_label = (dc.status or "pendente").upper()
            motivos.append(f"Denúncia de Chat #{dc.id} ({status_label}): {dc.motivo}")

        # 2. Denúncias em Obras publicadas pelo usuário
        denuncias_obras = []
        try:
            denuncias_obras = (
                db.query(Denuncia)
                .join(Postagem, Denuncia.idPostagem == Postagem.id)
                .filter(Postagem.idUsuario == u.id)
                .all()
            )
            for do in denuncias_obras:
                status_do = (do.status or "PENDENTE").upper()
                motivos.append(f"Obra #{do.idPostagem} denunciada ({status_do}): {do.motivo}")
        except Exception:
            pass

        # 3. Obras em Quarentena ou Rejeitadas
        obras_irregulares = (
            db.query(Postagem)
            .filter(
                Postagem.idUsuario == u.id,
                Postagem.status.in_(["quarentena", "rejeitada"]),
            )
            .all()
        )
        qtd_quarentena = sum(1 for o in obras_irregulares if o.status == "quarentena" and not o.deletado)
        qtd_rejeitadas = sum(1 for o in obras_irregulares if o.status == "rejeitada")
        if qtd_quarentena > 0:
            motivos.append(f"{qtd_quarentena} obra(s) retida(s) na Quarentena aguardando revisão")
        if qtd_rejeitadas > 0:
            motivos.append(f"{qtd_rejeitadas} obra(s) rejeitada(s) por violação das diretrizes")

        # 4. Sanções registradas nos Logs de Auditoria
        logs_usuario = (
            db.query(LogAuditoria)
            .filter(LogAuditoria.alvo_tipo == "usuario", LogAuditoria.alvo_id == u.id)
            .order_by(LogAuditoria.criado_em.desc())
            .all()
        )
        for lu in logs_usuario[:3]:
            if lu.detalhes:
                motivos.append(f"Histórico disciplinar: {lu.detalhes}")

        # 5. Status de suspensão ou banimento direto no perfil
        susp_ate = u.suspenso_ate
        if susp_ate:
            susp_check = susp_ate.replace(tzinfo=None) if susp_ate.tzinfo else susp_ate
            if susp_check > agora_naive and not any("suspenso" in m.lower() for m in motivos):
                motivos.append(f"Conta suspensa temporariamente até {susp_ate.strftime('%d/%m/%Y')}")

        if u.ativo is False and not any("banido" in m.lower() for m in motivos):
            motivos.append("Conta banida / desativada pela administração")

        if not motivos:
            motivos.append("Consultado via busca manual (nenhuma infração ativa)")

        total_den_chat = len(denuncias_chat)
        total_den_obras = len(denuncias_obras)
        total_geral_den = total_den_chat + total_den_obras

        resposta.append(
            UsuarioSinalizadoResposta(
                id=u.id,
                nome=u.nome,
                email=u.email,
                fotoPerfil=u.fotoPerfil,
                total_denuncias=total_geral_den,
                total_denuncias_chat=total_den_chat,
                total_denuncias_obras=total_den_obras,
                obras_irregulares=len(obras_irregulares),
                total_sancoes=len(logs_usuario),
                motivos_sinalizacao=motivos,
                ativo=u.ativo if u.ativo is not None else True,
                suspenso_ate=u.suspenso_ate,
                papel=getattr(u, "papel", None) or getattr(u, "tipo_conta", "artista"),
            )
        )

    # Ordena priorizando quem tem mais denúncias e infrações
    resposta.sort(
        key=lambda x: (x.total_denuncias, x.obras_irregulares, x.total_sancoes, x.id),
        reverse=True,
    )
    return resposta


# ======================================================================
# F) Gestão Completa do Desafio da Semana (Criar, Editar, Prazo, Retirar, Ativar, Rotacionar)
# ======================================================================
@router.get("/desafios", summary="Listar temas de Desafios Semanais cadastrados")
def admin_listar_desafios(
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna todos os temas de desafios cadastrados, indicando qual está ativo,
    data de início, prazo em dias, data de término e dias restantes.
    """
    desafios = (
        db.query(Categoria)
        .filter(
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .order_by(desc(Categoria.desafio_ativo), Categoria.id.asc())
        .all()
    )
    return [_serializar_desafio(d) for d in desafios]


@router.post("/desafios", status_code=status.HTTP_201_CREATED, summary="Criar novo tema de Desafio Semanal")
def admin_criar_desafio(
    dados: DesafioCriarRequisicao,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Cria um novo tema para a fila de Desafios Semanais com prazo configurável
    e opção de ativação imediata. Registra ação no Log de Auditoria.
    """
    nome_limpo = dados.nomeCategoria.strip()
    if not nome_limpo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um nome válido para o tema do desafio.",
        )

    existente = (
        db.query(Categoria)
        .filter(func.lower(Categoria.nomeCategoria) == nome_limpo.lower())
        .first()
    )

    agora = datetime.now(timezone.utc)
    prazo = dados.prazo_dias or 7

    if existente:
        if not existente.deletado and existente.is_desafio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um tema de desafio ativo com este nome.",
            )
        # Reativa/converte categoria existente
        existente.nomeCategoria = nome_limpo
        existente.deletado = False
        existente.dataDelecao = None
        existente.is_desafio = True
        existente.prazo_dias = prazo
        novo_desafio = existente
    else:
        novo_desafio = Categoria(
            nomeCategoria=nome_limpo,
            is_desafio=True,
            desafio_ativo=False,
            prazo_dias=prazo,
            deletado=False,
        )
        db.add(novo_desafio)
        db.flush()

    if dados.ativar_agora:
        todos = (
            db.query(Categoria)
            .filter(Categoria.deletado == False, Categoria.is_desafio == True)
            .all()
        )
        for d in todos:
            d.desafio_ativo = False
        novo_desafio.desafio_ativo = True
        novo_desafio.data_inicio_desafio = agora
        novo_desafio.data_fim_desafio = agora + timedelta(days=prazo)

    log = LogAuditoria(
        moderador_id=moderador.id,
        acao="desafio_criado",
        alvo_tipo="desafio",
        alvo_id=novo_desafio.id,
        detalhes=(
            f"Novo tema de desafio '{novo_desafio.nomeCategoria}' criado com prazo de {prazo} dia(s)"
            + (" e ativado imediatamente." if dados.ativar_agora else " na fila circular.")
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(novo_desafio)

    return {
        "mensagem": f"Tema '{novo_desafio.nomeCategoria}' criado com sucesso!",
        "desafio": _serializar_desafio(novo_desafio),
    }


@router.patch("/desafios/{categoria_id}", summary="Editar nome ou prazo de um Desafio Semanal")
def admin_atualizar_desafio(
    categoria_id: int,
    dados: DesafioAtualizarRequisicao,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Atualiza o nome e/ou o prazo em dias de um tema de Desafio Semanal.
    """
    alvo = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .first()
    )
    if not alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tema de desafio semanal não encontrado.",
        )

    alteracoes = []
    if dados.nomeCategoria is not None and dados.nomeCategoria.strip():
        novo_nome = dados.nomeCategoria.strip()
        if novo_nome.lower() != alvo.nomeCategoria.lower():
            conflito = (
                db.query(Categoria)
                .filter(
                    func.lower(Categoria.nomeCategoria) == novo_nome.lower(),
                    Categoria.id != alvo.id,
                )
                .first()
            )
            if conflito:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe outra categoria ou desafio com este nome.",
                )
            alteracoes.append(f"nome alterado de '{alvo.nomeCategoria}' para '{novo_nome}'")
            alvo.nomeCategoria = novo_nome

    if dados.prazo_dias is not None:
        alvo.prazo_dias = dados.prazo_dias
        alteracoes.append(f"prazo definido para {dados.prazo_dias} dia(s)")

    agora = datetime.now(timezone.utc)
    prazo_atual = getattr(alvo, "prazo_dias", 7) or 7

    if dados.reiniciar_prazo and alvo.desafio_ativo:
        alvo.data_inicio_desafio = agora
        alvo.data_fim_desafio = agora + timedelta(days=prazo_atual)
        alteracoes.append("contagem de prazo reiniciada a partir de hoje")
    elif alvo.desafio_ativo and alvo.data_inicio_desafio:
        inicio = alvo.data_inicio_desafio
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        alvo.data_fim_desafio = inicio + timedelta(days=prazo_atual)

    resumo_alt = ", ".join(alteracoes) if alteracoes else "configurações revisadas"
    log = LogAuditoria(
        moderador_id=moderador.id,
        acao="desafio_atualizado",
        alvo_tipo="desafio",
        alvo_id=alvo.id,
        detalhes=f"Desafio #{alvo.id} ('{alvo.nomeCategoria}') atualizado: {resumo_alt}.",
    )
    db.add(log)
    db.commit()
    db.refresh(alvo)

    return {
        "mensagem": f"Desafio '{alvo.nomeCategoria}' atualizado com sucesso!",
        "desafio": _serializar_desafio(alvo),
    }


@router.delete("/desafios/{categoria_id}", summary="Retirar / excluir um tema de Desafio Semanal")
def admin_remover_desafio(
    categoria_id: int,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Remove (soft delete) um tema da fila de Desafios Semanais.
    Se o tema removido estava ativo, ativa automaticamente o próximo tema disponível.
    """
    alvo = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .first()
    )
    if not alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tema de desafio semanal não encontrado.",
        )

    estava_ativo = bool(alvo.desafio_ativo)
    nome_removido = alvo.nomeCategoria
    agora = datetime.now(timezone.utc)

    alvo.desafio_ativo = False
    alvo.deletado = True
    alvo.dataDelecao = agora

    novo_ativo_nome = None
    if estava_ativo:
        proximo = (
            db.query(Categoria)
            .filter(
                Categoria.deletado == False,
                Categoria.is_desafio == True,
                Categoria.id != alvo.id,
            )
            .order_by(Categoria.id.asc())
            .first()
        )
        if proximo:
            prazo_prox = getattr(proximo, "prazo_dias", 7) or 7
            proximo.desafio_ativo = True
            proximo.data_inicio_desafio = agora
            proximo.data_fim_desafio = agora + timedelta(days=prazo_prox)
            novo_ativo_nome = proximo.nomeCategoria

    detalhe_log = f"Tema de desafio '{nome_removido}' (ID #{alvo.id}) retirado da plataforma."
    if novo_ativo_nome:
        detalhe_log += f" Tema '{novo_ativo_nome}' assumiu automaticamente como desafio ativo."

    log = LogAuditoria(
        moderador_id=moderador.id,
        acao="desafio_removido",
        alvo_tipo="desafio",
        alvo_id=alvo.id,
        detalhes=detalhe_log,
    )
    db.add(log)
    db.commit()

    return {
        "mensagem": f"Tema '{nome_removido}' retirado com sucesso!"
        + (f" Novo tema ativo: '{novo_ativo_nome}'." if novo_ativo_nome else ""),
        "id_removido": alvo.id,
    }


@router.post("/desafios/{categoria_id}/ativar", summary="Ativar manualmente um tema de Desafio Semanal")
def admin_ativar_desafio(
    categoria_id: int,
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Ativa um tema específico de desafio, calcula sua data limite e registra Log de Auditoria.
    """
    alvo = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .first()
    )

    if not alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria de desafio semanal não encontrada.",
        )

    todos = (
        db.query(Categoria)
        .filter(
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .all()
    )

    for d in todos:
        d.desafio_ativo = False

    agora = datetime.now(timezone.utc)
    prazo = getattr(alvo, "prazo_dias", 7) or 7
    alvo.desafio_ativo = True
    alvo.data_inicio_desafio = agora
    alvo.data_fim_desafio = agora + timedelta(days=prazo)

    log = LogAuditoria(
        moderador_id=moderador.id,
        acao="desafio_ativado",
        alvo_tipo="desafio",
        alvo_id=alvo.id,
        detalhes=f"Desafio Semanal alterado manualmente para '{alvo.nomeCategoria}' (prazo de {prazo} dias).",
    )
    db.add(log)
    db.commit()
    db.refresh(alvo)

    return {
        "mensagem": f"Desafio Semanal alterado com sucesso para '{alvo.nomeCategoria}'!",
        "desafio": _serializar_desafio(alvo),
    }


@router.post("/desafios/rotacionar", summary="Forçar rotação para o próximo tema semanal")
def admin_rotacionar_desafio(
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Força a rotação imediata para o próximo tema da lista circular e registra Log de Auditoria.
    """
    desafios = (
        db.query(Categoria)
        .filter(
            Categoria.deletado == False,
            Categoria.is_desafio == True,
        )
        .order_by(Categoria.id.asc())
        .all()
    )

    if not desafios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum tema de desafio semanal encontrado.",
        )

    ativo = next((d for d in desafios if d.desafio_ativo), None)
    nome_anterior = ativo.nomeCategoria if ativo else "Nenhum"
    for d in desafios:
        d.desafio_ativo = False

    proximo = None
    if ativo:
        proximo = next((d for d in desafios if d.id > ativo.id), None)
    if not proximo:
        proximo = desafios[0]

    agora = datetime.now(timezone.utc)
    prazo = getattr(proximo, "prazo_dias", 7) or 7
    proximo.desafio_ativo = True
    proximo.data_inicio_desafio = agora
    proximo.data_fim_desafio = agora + timedelta(days=prazo)

    log = LogAuditoria(
        moderador_id=moderador.id,
        acao="desafio_rotacionado",
        alvo_tipo="desafio",
        alvo_id=proximo.id,
        detalhes=f"Rotação manual de desafio: de '{nome_anterior}' para '{proximo.nomeCategoria}' ({prazo} dias).",
    )
    db.add(log)
    db.commit()
    db.refresh(proximo)

    return {
        "mensagem": f"Desafio Semanal rotacionado com sucesso para '{proximo.nomeCategoria}'!",
        "desafio": _serializar_desafio(proximo),
    }
