from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.controllers.auth_controller import obter_usuario_opcional
from app.models.usuario_model import Usuario
from app.services.trending_service import TrendingService

router = APIRouter(tags=["Trending / Explorar Em Alta"])

@router.get("/explorar/em-alta", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK, summary="Obter as 50 obras em alta (Trending)")
@router.get("/explorar/em-alta/", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK, include_in_schema=False)
@router.get("/postagens/trending", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK, include_in_schema=False)
def obter_em_alta(
    usuario_atual: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db)
):
    """
    Entrega o TOP 50 de obras em alta calculadas pelo algoritmo de Time Decay.
    Resposta rápida lendo diretamente do Cache Redis.
    """
    user_id = usuario_atual.id if usuario_atual else None
    return TrendingService.obter_em_alta(db, user_id)
