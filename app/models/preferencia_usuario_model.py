from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PreferenciaUsuario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'preferenciausuario' no PostgreSQL.
    Armazena os interesses/categorias favoritos de cada artista/usuário.
    """
    __tablename__ = "preferenciausuario"

    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), primary_key=True)
    idCategoria: Mapped[int] = mapped_column("idcategoria", ForeignKey("categoria.id"), primary_key=True)
    dataSelecao: Mapped[Optional[datetime]] = mapped_column("dataselecao", DateTime, server_default=func.now())

    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="joined")
    categoria: Mapped["Categoria"] = relationship("Categoria", lazy="joined")

    def __repr__(self) -> str:
        return f"<PreferenciaUsuario(idUsuario={self.idUsuario}, idCategoria={self.idCategoria})>"
