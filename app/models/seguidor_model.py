from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Seguidor(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'seguidor' no PostgreSQL.
    Armazena o relacionamento de seguir entre usuários com chave composta (idseguidor, idseguido).
    """
    __tablename__ = "seguidor"

    idSeguidor: Mapped[int] = mapped_column("idseguidor", ForeignKey("usuario.id"), primary_key=True)
    idSeguido: Mapped[int] = mapped_column("idseguido", ForeignKey("usuario.id"), primary_key=True)
    dataSeguiu: Mapped[Optional[datetime]] = mapped_column("dataseguiu", DateTime, server_default=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Seguidor(idSeguidor={self.idSeguidor}, idSeguido={self.idSeguido})>"
