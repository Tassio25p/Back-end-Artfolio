from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Conversa(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'conversa' no PostgreSQL.

    Este modelo mapeia as conversas (chats) entre usuários da plataforma,
    incluindo controle de deleção lógica (soft delete).
    """
    __tablename__ = "conversa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Conversa(id={self.id}, dataCriacao={self.dataCriacao})>"
