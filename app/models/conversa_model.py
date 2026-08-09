from sqlalchemy import Column, Integer, Boolean, DateTime, func
from app.database import Base

class Conversa(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'conversa' no PostgreSQL.

    Este modelo mapeia as conversas (chats) entre usuários da plataforma,
    incluindo controle de deleção lógica (soft delete).
    """
    __tablename__ = "conversa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    def __repr__(self):
        return f"<Conversa(id={self.id}, dataCriacao={self.dataCriacao})>"
