from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.denuncia_schema import DenunciaResposta, DenunciaAtualizarStatus
from app.services.denuncia_service import DenunciaService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario

router = APIRouter(prefix="/admin", tags=["Administração / Moderação"])


@router.get(
    "/denuncias",
    response_model=List[DenunciaResposta],
    status_code=status.HTTP_200_OK,
    summary="Listar todas as denúncias (Admin/Moderador)"
)
@router.get(
    "/denuncias/",
    response_model=List[DenunciaResposta],
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def listar_denuncias(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todas as denúncias enviadas para análise da moderação.
    Requer função de admin ou moderador.
    """
    return DenunciaService.listar_denuncias(db, usuario_atual.tipo_conta)


@router.patch(
    "/denuncias/{id}",
    response_model=DenunciaResposta,
    status_code=status.HTTP_200_OK,
    summary="Atualizar status da denúncia (Admin/Moderador)"
)
def atualizar_status_denuncia(
    id: int,
    dados: DenunciaAtualizarStatus,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Atualiza o status de uma denúncia ('PENDENTE', 'EM_ANALISE', 'RESOLVIDA', 'REJEITADA').
    """
    return DenunciaService.atualizar_status(db, id, dados, usuario_atual.tipo_conta)
