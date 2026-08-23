from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notificacao_schema import (
    NotificacaoListResposta,
    NotificacaoContadorResposta,
    NotificacaoResposta
)
from app.services.notificacao_service import NotificacaoService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get(
    "",
    response_model=NotificacaoListResposta,
    status_code=status.HTTP_200_OK,
    summary="Listar notificações do usuário autenticado"
)
@router.get(
    "/",
    response_model=NotificacaoListResposta,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def listar_notificacoes(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todas as notificações ativas do usuário autenticado,
    ordenadas das mais recentes para as mais antigas.
    """
    items = NotificacaoService.listar_notificacoes(db, usuario_atual.id)
    return {"items": items}


@router.get(
    "/nao-lidas",
    response_model=NotificacaoContadorResposta,
    status_code=status.HTTP_200_OK,
    summary="Contar notificações não lidas"
)
def contar_nao_lidas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a quantidade total de notificações não lidas do usuário autenticado.
    Utiliza cache Redis com fallback para o PostgreSQL.
    """
    qtd = NotificacaoService.contar_nao_lidas(db, usuario_atual.id)
    return {"quantidade": qtd}


@router.patch(
    "/ler-todas",
    status_code=status.HTTP_200_OK,
    summary="Marcar todas as notificações como lidas"
)
def marcar_todas_como_lidas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Marca todas as notificações ativas do usuário autenticado como lidas.
    """
    return NotificacaoService.marcar_todas_como_lidas(db, usuario_atual.id)


@router.patch(
    "/{id}/ler",
    response_model=NotificacaoResposta,
    status_code=status.HTTP_200_OK,
    summary="Marcar uma notificação como lida"
)
def marcar_como_lida(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Marca uma notificação específica do usuário autenticado como lida.
    Retorna erro HTTP 403 se a notificação pertencer a outro usuário.
    """
    return NotificacaoService.marcar_como_lida(db, usuario_atual.id, id)


@router.delete(
    "/todas",
    status_code=status.HTTP_200_OK,
    summary="Excluir todas as notificações"
)
@router.delete(
    "/todas/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def deletar_todas_notificacoes(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Exclui todas as notificações do usuário autenticado.
    """
    return NotificacaoService.deletar_todas(db, usuario_atual.id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Excluir uma notificação"
)
def deletar_notificacao(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Realiza o soft delete de uma notificação do usuário autenticado.
    Retorna erro HTTP 403 se a notificação pertencer a outro usuário.
    """
    return NotificacaoService.deletar_notificacao(db, usuario_atual.id, id)
