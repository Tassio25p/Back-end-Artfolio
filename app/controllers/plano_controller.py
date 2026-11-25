from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.plano_schema import PlanoResposta, MeuPlanoResposta
from app.services.plano_service import PlanoService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario

router = APIRouter(prefix="/planos", tags=["Planos e Assinaturas"])

@router.get("", response_model=List[PlanoResposta], status_code=status.HTTP_200_OK, summary="Listar planos disponíveis")
@router.get("/", response_model=List[PlanoResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_planos(db: Session = Depends(get_db)):
    """
    Retorna a lista de planos cadastrados na plataforma (Free, Pro, Boost).
    """
    return PlanoService.listar_planos(db)

@router.get("/meu-plano", response_model=MeuPlanoResposta, status_code=status.HTTP_200_OK, summary="Obter dados do plano do usuário logado")
@router.get("/meu-plano/", response_model=MeuPlanoResposta, status_code=status.HTTP_200_OK, include_in_schema=False)
def obter_meu_plano(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna as permissões e dados da assinatura atual do usuário logado.
    """
    return PlanoService.obter_meu_plano(db, usuario_atual)

@router.post("/assinar/{plano_id}", response_model=MeuPlanoResposta, status_code=status.HTTP_200_OK, summary="Assinar ou trocar de plano")
def assinar_plano(
    plano_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Ativa uma nova assinatura para o usuário autenticado no plano selecionado.
    """
    return PlanoService.assinar_plano(db, usuario_atual, plano_id)
