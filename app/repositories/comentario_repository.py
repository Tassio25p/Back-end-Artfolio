from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.comentario_model import Comentario


class ComentarioRepository:
    """
    Repositório de dados para a entidade Comentario.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def listar_por_postagem(db: Session, postagem_id: int) -> List[Comentario]:
        """
        Lista todos os comentários ativos de uma postagem, ordenados por data.
        """
        return db.query(Comentario).filter(
            Comentario.idPostagem == postagem_id,
            Comentario.deletado == False
        ).order_by(Comentario.dataCriacao.asc()).all()

    @staticmethod
    def buscar_por_id(db: Session, comentario_id: int) -> Optional[Comentario]:
        """
        Busca um comentário ativo pelo seu ID.
        """
        return db.query(Comentario).filter(
            Comentario.id == comentario_id,
            Comentario.deletado == False
        ).first()

    @staticmethod
    def criar(db: Session, comentario: Comentario) -> Comentario:
        """
        Persiste um novo comentário no banco de dados.
        """
        db.add(comentario)
        db.commit()
        db.refresh(comentario)
        return comentario

    @staticmethod
    def deletar(db: Session, comentario: Comentario) -> None:
        """
        Realiza o soft delete de um comentário, seguindo o padrão do projeto.
        """
        comentario.deletado = True
        comentario.dataDelecao = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def contar_por_postagem(db: Session, postagem_id: int) -> int:
        """
        Conta o número total de comentários ativos de uma postagem.
        """
        return db.query(func.count(Comentario.id)).filter(
            Comentario.idPostagem == postagem_id,
            Comentario.deletado == False
        ).scalar() or 0
