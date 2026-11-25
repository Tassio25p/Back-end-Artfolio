from app.models.usuario_model import Usuario
from app.models.conversa_model import Conversa
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class ConversaUsuario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'conversausuario' no PostgreSQL.

    Este modelo mapeia a tabela associativa (N:N) entre conversas e usuários,
    utilizando chave primária composta (idConversa, idUsuario).
    """
    __tablename__ = "conversausuario"

    idConversa: Mapped[int] = mapped_column("idconversa", ForeignKey("conversa.id"), primary_key=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), primary_key=True)
    dataEntrada: Mapped[Optional[datetime]] = mapped_column("dataentrada", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    conversa: Mapped[Conversa] = relationship(Conversa, lazy="joined")
    usuario: Mapped[Usuario] = relationship(Usuario, lazy="joined")

    def __repr__(self) -> str:
        return f"<ConversaUsuario(idConversa={self.idConversa}, idUsuario={self.idUsuario})>"
