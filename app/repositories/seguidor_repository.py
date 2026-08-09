from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.seguidor_model import Seguidor


class SeguidorRepository:
    """
    Repositório de dados para a entidade Seguidor.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def buscar(db: Session, seguidor_id: int, seguido_id: int) -> Optional[Seguidor]:
        """
        Verifica se um usuário já segue outro.
        """
        return db.query(Seguidor).filter(
            Seguidor.idSeguidor == seguidor_id,
            Seguidor.idSeguido == seguido_id
        ).first()

    @staticmethod
    def criar(db: Session, seguidor: Seguidor) -> Seguidor:
        """
        Persiste um novo relacionamento de seguir no banco de dados.
        """
        db.add(seguidor)
        db.commit()
        db.refresh(seguidor)
        return seguidor

    @staticmethod
    def deletar(db: Session, seguidor: Seguidor) -> None:
        """
        Remove o relacionamento de seguir do banco de dados.
        """
        db.delete(seguidor)
        db.commit()

    @staticmethod
    def contar_seguidores(db: Session, usuario_id: int) -> int:
        """
        Conta quantas pessoas seguem um usuário específico.
        """
        return db.query(func.count(Seguidor.id)).filter(
            Seguidor.idSeguido == usuario_id
        ).scalar() or 0

    @staticmethod
    def contar_seguindo(db: Session, usuario_id: int) -> int:
        """
        Conta quantas pessoas um usuário está seguindo.
        """
        return db.query(func.count(Seguidor.id)).filter(
            Seguidor.idSeguidor == usuario_id
        ).scalar() or 0
