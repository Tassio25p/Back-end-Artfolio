import json
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notificacao_schema import (
    NotificacoesPaginadasResposta,
    NotificacaoResposta,
    NotificacaoContadorResposta,
    NotificacaoAcaoLoteResposta,
    NotificacaoAcaoResposta,
)
from app.services.notificacao_service import NotificacaoService
from app.controllers.auth_controller import obter_usuario_atual, get_current_user
from app.models.usuario_model import Usuario
from app.core.websocket_manager import manager

# Router padronizado para as rotas da Central de Notificações
router = APIRouter(tags=["Notificações"])


# =====================================================================
# 1. WEBSOCKET DE NOTIFICAÇÕES EM TEMPO REAL
# =====================================================================

@router.websocket("/ws/{user_id}")
@router.websocket("/ws/notificacoes/{user_id}")
async def websocket_notificacoes(websocket: WebSocket, user_id: int):
    """
    Endpoint WebSocket para recebimento de notificações em tempo real via Redis Pub/Sub.
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    payload = json.loads(data)
                    tipo = str(payload.get("tipo", "")).upper()
                    if tipo in ("DIGITANDO", "TYPING"):
                        conversa_id = payload.get("conversa_id") or payload.get("idConversa")
                        if conversa_id:
                            from app.database import SessionLocal
                            from app.repositories.conversa_repository import ConversaRepository
                            db_ws = SessionLocal()
                            try:
                                participantes = ConversaRepository.buscar_participantes(db_ws, int(conversa_id))
                                for p in participantes:
                                    if p.idUsuario != user_id:
                                        await manager.send_personal_message(p.idUsuario, payload)
                            finally:
                                db_ws.close()
                    elif tipo in ("MENSAGEM", "NOVA_MENSAGEM", "CHAT_MESSAGE"):
                        conversa_id = payload.get("conversa_id") or payload.get("idConversa")
                        conteudo = payload.get("conteudo") or payload.get("mensagem")
                        if conversa_id and conteudo:
                            from app.database import SessionLocal
                            from app.services.mensagem_service import MensagemService
                            from app.schemas.mensagem_schema import MensagemCriar
                            db_ws = SessionLocal()
                            try:
                                await MensagemService.enviar_mensagem(
                                    db=db_ws,
                                    remetente_id=user_id,
                                    conversa_id=int(conversa_id),
                                    dados=MensagemCriar(conteudo=str(conteudo))
                                )
                            finally:
                                db_ws.close()

                except Exception:
                    pass
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket, user_id)


# =====================================================================
# 2. ENDPOINTS PRINCIPAIS PADRONIZADOS DA CENTRAL DE NOTIFICAÇÕES
# =====================================================================

@router.get(
    "",
    response_model=NotificacoesPaginadasResposta,
    status_code=status.HTTP_200_OK,
    summary="Listar notificações paginadas com filtros"
)
@router.get(
    "/",
    response_model=NotificacoesPaginadasResposta,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def listar_notificacoes(
    tipo: Optional[str] = Query(
        None,
        description="Filtro opcional por tipo/categoria (ex: 'mensagem', 'proposta', 'curtida', 'comentario', 'seguidor', 'interacao', 'sistema')"
    ),
    apenas_nao_lidas: bool = Query(
        False,
        description="Se True, retorna apenas notificações não lidas"
    ),
    limite: int = Query(
        20,
        ge=1,
        le=100,
        description="Quantidade máxima de registros retornados"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Quantidade de registros a pular para paginação"
    ),
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista paginada de notificações do usuário autenticado:
    - total_nao_lidas: contagem global de não lidas do usuário
    - total: total de registros que satisfazem os filtros
    - notificacoes: lista ordenada por criado_em DESC
    """
    return NotificacaoService.listar_notificacoes_paginadas(
        db=db,
        usuario_id=usuario_atual.id,
        tipo=tipo,
        apenas_nao_lidas=apenas_nao_lidas,
        limite=limite,
        offset=offset
    )


@router.patch(
    "/ler-todas",
    response_model=NotificacaoAcaoLoteResposta,
    status_code=status.HTTP_200_OK,
    summary="Marcar todas as notificações do usuário como lidas"
)
def marcar_todas_como_lidas(
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza em lote todas as notificações onde usuario_id == usuario_atual.id
    e lida == False para lida = True.
    Retorna {'status': 'sucesso', 'total_atualizadas': count}.
    """
    return NotificacaoService.marcar_todas_como_lidas(db, usuario_atual.id)


@router.patch(
    "/{notificacao_id}/ler",
    response_model=NotificacaoResposta,
    status_code=status.HTTP_200_OK,
    summary="Marcar uma notificação específica como lida"
)
def marcar_como_lida(
    notificacao_id: int,
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Valida se notificacao.usuario_id == usuario_atual.id.
    Atualiza lida = True, persiste no banco e retorna a notificação atualizada.
    """
    notif = NotificacaoService.marcar_como_lida(db, usuario_atual.id, notificacao_id)
    return NotificacaoService.serializar_notificacao(notif)


@router.delete(
    "/todas",
    status_code=status.HTTP_200_OK,
    summary="Excluir todas as notificações (soft delete)",
    include_in_schema=True
)
def deletar_todas(
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Realiza soft delete em todas as notificações do usuário autenticado.
    """
    return NotificacaoService.deletar_todas(db, usuario_atual.id)


@router.delete(
    "/{notificacao_id}",
    response_model=NotificacaoAcaoResposta,
    status_code=status.HTTP_200_OK,
    summary="Excluir uma notificação específica (soft delete)"
)
def deletar_notificacao(
    notificacao_id: int,
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite ao usuário remover um item específico do seu histórico.
    Remove (soft delete) apenas se pertencer ao usuario_atual.id.
    """
    return NotificacaoService.deletar_notificacao(db, usuario_atual.id, notificacao_id)


# =====================================================================
# 3. ENDPOINTS DE RETROCOMPATIBILIDADE
# =====================================================================

@router.get(
    "/todas",
    status_code=status.HTTP_200_OK,
    summary="Listar todas as notificações como array direto (legado)"
)
def listar_todas(
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todas as notificações do usuário autenticado no formato array [],
    garantindo compatibilidade com implementações anteriores do frontend.
    """
    return NotificacaoService.listar_notificacoes(db, usuario_atual.id)


@router.get(
    "/nao-lidas",
    response_model=NotificacaoContadorResposta,
    status_code=status.HTTP_200_OK,
    summary="Contar notificações não lidas"
)
def contar_nao_lidas(
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna a contagem de notificações não lidas do usuário autenticado.
    """
    qtd = NotificacaoService.contar_nao_lidas(db, usuario_atual.id)
    return {"quantidade": qtd}
