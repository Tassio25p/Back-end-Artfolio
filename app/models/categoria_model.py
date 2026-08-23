from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Categoria(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'categoria' no PostgreSQL.
    """
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nomeCategoria: Mapped[str] = mapped_column("nomecategoria", String(50), unique=True, nullable=False)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Categoria(id={self.id}, nomeCategoria='{self.nomeCategoria}')>"
