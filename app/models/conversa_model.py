from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, String, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Conversa(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'conversa' no PostgreSQL.

    Este modelo mapeia as conversas (chats diretos e em grupo) entre usuários da plataforma,
    incluindo controle de deleção lógica (soft delete).
    """
    __tablename__ = "conversa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    is_grupo: Mapped[bool] = mapped_column("is_grupo", Boolean, default=False)
    nome_grupo: Mapped[Optional[str]] = mapped_column("nome_grupo", String(100), nullable=True)
    foto_grupo: Mapped[Optional[str]] = mapped_column("foto_grupo", String(255), nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column("admin_id", Integer, ForeignKey("usuario.id"), nullable=True)
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Conversa(id={self.id}, is_grupo={self.is_grupo}, nome_grupo='{self.nome_grupo}', dataCriacao={self.dataCriacao})>"
