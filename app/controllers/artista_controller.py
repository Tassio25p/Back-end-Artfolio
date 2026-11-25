from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.artista_schema import ArtistaResposta
from app.services.artista_service import ArtistaService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.services.seguidor_service import SeguidorService


router = APIRouter(tags=["Artistas"])

# endpoint de listagem de artistas
@router.get("/artistas", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, summary="Listar artistas")
@router.get("/artistas/", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_artistas(db: Session = Depends(get_db)):
    """
    Retorna todos os artistas ativos cadastrados na plataforma.
    """
    return ArtistaService.listar_artistas(db)

# endpoint de busca de artistas por nome, ou parte do nome
@router.get("/artistas/busca", response_model=List[ArtistaResposta], status_code=status.HTTP_200_OK, summary="Buscar artistas por nome")
def buscar_artistas_por_nome(
    nome: str = Query(..., min_length=1, description="Nome ou parte do nome do artista"),
    db: Session = Depends(get_db)
):
    """
    Busca artistas pelo nome (busca parcial, case-insensitive).
    """
    return ArtistaService.buscar_artistas_por_nome(db, nome)



# endpoint de obtenção de artista por ID
@router.get("/artistas/{id}", response_model=ArtistaResposta, status_code=status.HTTP_200_OK, summary="Obter artista por ID")
def obter_artista_por_id(id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um artista específico através do seu ID.
    """
    return ArtistaService.buscar_artista_por_id(db, id)

@router.get("/artistas/{id}/estatisticas-painel", status_code=status.HTTP_200_OK, summary="Obter painel de estatísticas e pódio de categorias do artista")
def obter_estatisticas_artista(id: int, db: Session = Depends(get_db)):
    """
    Retorna métricas consolidadas, contadores e pódio de categorias de maior engajamento.
    Disponível para contas Pro e Boost (com modo de demonstração para Free).
    """
    from app.services.estatistica_service import EstatisticaService
    return EstatisticaService.obter_painel_artista(db, id)

# endpoint de seguir artista
@router.post("/artistas/{id}/seguir", status_code=status.HTTP_200_OK, summary="Seguir ou alternar seguir artista")
def seguir_artista(id: int, usuario_atual: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """
    Permite seguir ou alternar seguir um artista por sua rota /artistas/{id}/seguir.
    """
    return SeguidorService.alternar_seguir(db, usuario_atual.id, id)

# endpoint de deixar de seguir artista
@router.delete("/artistas/{id}/seguir", status_code=status.HTTP_200_OK, summary="Deixar de seguir artista")
def deixar_de_seguir_artista(id: int, usuario_atual: Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    """
    Permite deixar de seguir um artista por sua rota /artistas/{id}/seguir.
    """
    return SeguidorService.deixar_de_seguir(db, usuario_atual.id, id)
