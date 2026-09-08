from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc

from app.database import get_db
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.models.postagem_model import Postagem
from app.models.denuncia_chat_model import DenunciaChat
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.models.log_auditoria_model import LogAuditoria

from app.schemas.admin_schema import (
    AdminMetricasResposta,
    JulgarObraRequisicao,
    SancaoUsuarioRequisicao,
    AtualizarDenunciaRequisicao,
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
    - usuarios_sinalizados: usuários com denúncias registradas
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

    usuarios_sinalizados = (
        db.query(func.count(func.distinct(DenunciaChat.denunciado_id)))
        .filter(DenunciaChat.status == "pendente")
        .scalar()
        or 0
    )

    # Se não houver usuários sinalizados pendentes, traz a contagem geral de denunciados
    if usuarios_sinalizados == 0:
        usuarios_sinalizados = (
            db.query(func.count(func.distinct(DenunciaChat.denunciado_id))).scalar() or 0
        )

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

    # Buscar todas as mensagens da conversa SEM FILTRAR deletadas
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
    denuncia.resolvido_em = datetime.utcnow()

    # Registro de auditoria obrigatório
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
        cats = [c.nome for c in o.categorias] if o.categorias else []
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
    - Se 'aprovar': status vira 'publicada', gerando notificação positiva e log.
    - Se 'rejeitar': arquiva a obra (status 'rejeitada', deletado=True) e gera
      notificação do sistema com o motivo para o artista.
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

        # Notificação para o artista
        notif = Notificacao(
            idUsuario=obra.idUsuario,
            tipo="sistema",
            titulo="Sua obra foi aprovada!",
            mensagem="Parabéns! Sua publicação foi revisada pela equipe de moderação e agora está pública no feed do Artfolio.",
            idPostagem=obra.id,
        )
        db.add(notif)

        # Log de auditoria
        log = LogAuditoria(
            moderador_id=moderador.id,
            acao="obra_aprovada",
            alvo_tipo="obra",
            alvo_id=obra.id,
            detalhes=f"Obra #{obra.id} aprovada e publicada pelo moderador {moderador.nome}.",
        )
        db.add(log)

    else:  # rejeitar
        motivo = dados.motivo.strip() if dados.motivo else "Violação das diretrizes da comunidade."
        obra.status = "rejeitada"
        obra.deletado = True
        obra.dataDelecao = datetime.utcnow()

        # Notificação formal para o artista
        notif = Notificacao(
            idUsuario=obra.idUsuario,
            tipo="sistema",
            titulo="Sua obra foi rejeitada pela moderação",
            mensagem=f"Sua publicação foi removida por não atender às diretrizes da plataforma. Motivo: {motivo}",
            idPostagem=obra.id,
        )
        db.add(notif)

        # Log de auditoria
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
    Aplica uma sanção formal ao usuário infrator:
    - 'advertir': gera Notificação formal no sistema e log.
    - 'suspender': define suspenso_ate = now + X dias, gera notificação e log.
    - 'banir': desativa a conta (ativo=False, deletado=True) e gera log.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Impedir sanções a outros moderadores/admins
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
        data_fim = datetime.utcnow() + timedelta(days=dias)
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
        usuario.dataDelecao = datetime.utcnow()

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
# E) Logs de Auditoria e Usuários Sinalizados
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
        .order_by(LogAuditoria.criado_em.desc())
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
    summary="Listar usuários sinalizados por denúncias ou suspensões",
)
def listar_usuarios_sinalizados(
    moderador: Usuario = Depends(exigir_moderador_ou_admin),
    db: Session = Depends(get_db),
):
    """
    Retorna os usuários que possuem denúncias abertas, advertências,
    suspensões ativas ou que foram banidos.
    """
    # Usuários com contagem de denúncias
    subquery_denuncias = (
        db.query(
            DenunciaChat.denunciado_id.label("usuario_id"),
            func.count(DenunciaChat.id).label("total"),
        )
        .group_by(DenunciaChat.denunciado_id)
        .subquery()
    )

    usuarios = (
        db.query(
            Usuario,
            func.coalesce(subquery_denuncias.c.total, 0).label("total_denuncias"),
        )
        .outerjoin(subquery_denuncias, Usuario.id == subquery_denuncias.c.usuario_id)
        .filter(
            or_(
                subquery_denuncias.c.total > 0,
                Usuario.ativo == False,
                Usuario.suspenso_ate != None,
            )
        )
        .order_by(desc("total_denuncias"), Usuario.id.desc())
        .all()
    )

    # Se não houver nenhum sinalizado no banco, traz os últimos usuários para exibição
    if not usuarios:
        usuarios_gerais = db.query(Usuario).order_by(Usuario.id.desc()).limit(10).all()
        return [
            UsuarioSinalizadoResposta(
                id=u.id,
                nome=u.nome,
                email=u.email,
                fotoPerfil=u.fotoPerfil,
                total_denuncias=0,
                ativo=u.ativo if hasattr(u, "ativo") else True,
                suspenso_ate=u.suspenso_ate if hasattr(u, "suspenso_ate") else None,
                papel=getattr(u, "papel", None) or getattr(u, "tipo_conta", "artista"),
            )
            for u in usuarios_gerais
        ]

    resposta: List[UsuarioSinalizadoResposta] = []
    for u, total_denuncias in usuarios:
        resposta.append(
            UsuarioSinalizadoResposta(
                id=u.id,
                nome=u.nome,
                email=u.email,
                fotoPerfil=u.fotoPerfil,
                total_denuncias=total_denuncias,
                ativo=u.ativo,
                suspenso_ate=u.suspenso_ate,
                papel=getattr(u, "papel", None) or getattr(u, "tipo_conta", "artista"),
            )
        )
    return resposta
