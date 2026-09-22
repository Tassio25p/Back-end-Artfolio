from app.models.usuario_model import Usuario
from datetime import datetime
from typing import Optional
from sqlalchemy import Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Comentario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'comentario' no PostgreSQL.
    Armazena os comentários dos usuários nas postagens com coluna 'datacomentario'.
    """
    __tablename__ = "comentario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False, index=True)
    idPostagem: Mapped[int] = mapped_column("idpostagem", ForeignKey("postagem.id"), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacomentario", DateTime, server_default=func.now(), nullable=True)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamento para trazer os dados do usuário que comentou
    usuario: Mapped[Usuario] = relationship(Usuario, lazy="joined")

    def __repr__(self) -> str:
        return f"<Comentario(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem})>"
