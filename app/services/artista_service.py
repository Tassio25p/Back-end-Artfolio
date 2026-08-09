from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.usuario_model import Usuario
from app.repositories.artista_repository import ArtistaRepository

class ArtistaService:
    """
    Serviço contendo as regras de negócio relacionadas aos Artistas.
    """

    @staticmethod
    def listar_artistas(db: Session) -> List[Usuario]:
        """
        Retorna a lista de todos os artistas ativos no sistema.
        """
        return ArtistaRepository.listar_todos(db)

    @staticmethod
    def buscar_artista_por_id(db: Session, artista_id: int) -> Usuario:
        """
        Busca um artista pelo ID. Lança HTTP 404 se não for encontrado.
        """
        artista = ArtistaRepository.buscar_por_id(db, artista_id)
        if not artista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artista não encontrado."
            )
        return artista

    @staticmethod
    def buscar_artistas_por_nome(db: Session, nome: str) -> List[Usuario]:
        """
        Busca artistas pelo nome (busca parcial).
        """
        return ArtistaRepository.buscar_por_nome(db, nome)
