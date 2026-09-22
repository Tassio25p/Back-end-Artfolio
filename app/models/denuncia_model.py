from app.models.postagem_model import Postagem
from app.models.usuario_model import Usuario
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Denuncia(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'denuncia' no PostgreSQL.

    Armazena as denúncias enviadas pelos usuários sobre obras/postagens.
    """
    __tablename__ = "denuncia"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False, index=True)  # Denunciante
    idPostagem: Mapped[int] = mapped_column("idpostagem", ForeignKey("postagem.id"), nullable=False, index=True)  # Obra denunciada
    motivo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")  # PENDENTE, EM_ANALISE, RESOLVIDA, REJEITADA
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idusuario", "idpostagem", name="uq_denuncia_usuario_postagem"),
    )

    usuario: Mapped[Usuario] = relationship(Usuario, lazy="joined")
    postagem: Mapped[Postagem] = relationship(Postagem, lazy="joined")

    def __repr__(self) -> str:
        return f"<Denuncia(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem}, motivo='{self.motivo}')>"
