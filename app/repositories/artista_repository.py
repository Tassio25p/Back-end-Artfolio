from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.usuario_model import Usuario

class ArtistaRepository:
    """
    Repositório de dados para consultas de Artistas.
    Artista é um Usuário com tipo_conta = 'artista'.
    """

    @staticmethod
    def listar_todos(db: Session) -> List[Usuario]:
        """
        Lista todos os artistas ativos no sistema.
        """
        return db.query(Usuario).filter(
            Usuario.tipo_conta == "artista",
            Usuario.deletado == False
        ).order_by(Usuario.nome).all()

    @staticmethod
    def buscar_por_id(db: Session, artista_id: int) -> Optional[Usuario]:
        """
        Busca um artista ativo pelo seu ID.
        """
        return db.query(Usuario).filter(
            Usuario.id == artista_id,
            Usuario.tipo_conta == "artista",
            Usuario.deletado == False
        ).first()

    @staticmethod
    def buscar_por_nome(db: Session, nome: str) -> List[Usuario]:
        """
        Busca artistas ativos pelo nome (busca parcial, case-insensitive).
        """
        return db.query(Usuario).filter(
            Usuario.tipo_conta == "artista",
            Usuario.deletado == False,
            Usuario.nome.ilike(f"%{nome}%")
        ).order_by(Usuario.nome).all()
