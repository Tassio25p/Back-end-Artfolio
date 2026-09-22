from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.controllers.auth_controller import obter_usuario_opcional
from app.models.usuario_model import Usuario
from app.schemas.postagem_schema import FeedItemResposta
from app.services.feed_service import FeedService

router = APIRouter(prefix="/feed", tags=["Feed"])

@router.get("", response_model=List[FeedItemResposta], status_code=status.HTTP_200_OK, summary="Obter feed de postagens")
@router.get("/", response_model=List[FeedItemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def obter_feed(
    usuario_atual: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db)
):
    """
    Retorna o feed cronológico de postagens ativas (mais recentes primeiro).
    """
    user_id: Optional[int] = usuario_atual.id if usuario_atual else None
    return FeedService.obter_feed(db, user_id)
