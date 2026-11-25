from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Curtida(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'curtida' no PostgreSQL.
    Armazena as curtidas (likes) dos usuários nas postagens com chave composta (idusuario, idpostagem).
    """
    __tablename__ = "curtida"

    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), primary_key=True)
    idPostagem: Mapped[int] = mapped_column("idpostagem", ForeignKey("postagem.id"), primary_key=True)
    dataCurtida: Mapped[Optional[datetime]] = mapped_column("datacurtida", DateTime, server_default=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Curtida(idUsuario={self.idUsuario}, idPostagem={self.idPostagem})>"
