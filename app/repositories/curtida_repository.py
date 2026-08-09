from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.curtida_model import Curtida


class CurtidaRepository:
    """
    Repositório de dados para a entidade Curtida.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def buscar(db: Session, usuario_id: int, postagem_id: int) -> Optional[Curtida]:
        """
        Verifica se um usuário já curtiu uma postagem específica.
        """
        return db.query(Curtida).filter(
            Curtida.idUsuario == usuario_id,
            Curtida.idPostagem == postagem_id
        ).first()

    @staticmethod
    def criar(db: Session, curtida: Curtida) -> Curtida:
        """
        Persiste uma nova curtida no banco de dados.
        """
        db.add(curtida)
        db.commit()
        db.refresh(curtida)
        return curtida

    @staticmethod
    def deletar(db: Session, curtida: Curtida) -> None:
        """
        Remove fisicamente uma curtida do banco de dados.
        """
        db.delete(curtida)
        db.commit()

    @staticmethod
    def contar_por_postagem(db: Session, postagem_id: int) -> int:
        """
        Conta o número total de curtidas de uma postagem.
        """
        return db.query(func.count(Curtida.id)).filter(
            Curtida.idPostagem == postagem_id
        ).scalar() or 0
