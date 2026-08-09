from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.artista_schema import ArtistaResposta
from app.services.artista_service import ArtistaService

router = APIRouter(tags=["Artistas"])

@router.get("/artistas", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, summary="Listar artistas")
@router.get("/artistas/", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_artistas(db: Session = Depends(get_db)):
    """
    Retorna todos os artistas ativos cadastrados na plataforma.
    """
    return ArtistaService.listar_artistas(db)

@router.get("/artistas/busca", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, summary="Buscar artistas por nome")
def buscar_artistas_por_nome(
    nome: str = Query(..., min_length=1, description="Nome ou parte do nome do artista"),
    db: Session = Depends(get_db)
):
    """
    Busca artistas pelo nome (busca parcial, case-insensitive).
    """
    return ArtistaService.buscar_artistas_por_nome(db, nome)

@router.get("/artistas/{id}", response_model=ArtistaResposta, status_code=status.HTTP_200_OK, summary="Obter artista por ID")
def obter_artista_por_id(id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um artista específico através do seu ID.
    """
    return ArtistaService.buscar_artista_por_id(db, id)
