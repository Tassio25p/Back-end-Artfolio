from app.models.conversa_model import Conversa
from app.models.usuario_model import Usuario
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class DenunciaChat(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'denuncia_chat' no PostgreSQL.

    Armazena as denúncias enviadas pelos usuários sobre conversas ou comportamentos no chat.
    """
    __tablename__ = "denuncia_chat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    denunciante_id: Mapped[int] = mapped_column("denunciante_id", ForeignKey("usuario.id"), nullable=False, index=True)
    denunciado_id: Mapped[int] = mapped_column("denunciado_id", ForeignKey("usuario.id"), nullable=False, index=True)
    conversa_id: Mapped[int] = mapped_column("conversa_id", ForeignKey("conversa.id"), nullable=False, index=True)
    motivo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    nota_moderador: Mapped[Optional[str]] = mapped_column("nota_moderador", Text, nullable=True)
    moderador_id: Mapped[Optional[int]] = mapped_column("moderador_id", ForeignKey("usuario.id"), nullable=True)
    resolvido_em: Mapped[Optional[datetime]] = mapped_column("resolvido_em", DateTime, nullable=True)
    criado_em: Mapped[Optional[datetime]] = mapped_column("criado_em", DateTime, server_default=func.now())

    # Relacionamentos
    denunciante: Mapped[Usuario] = relationship(Usuario, foreign_keys=[denunciante_id], lazy="joined")
    denunciado: Mapped[Usuario] = relationship(Usuario, foreign_keys=[denunciado_id], lazy="joined")
    conversa: Mapped[Conversa] = relationship(Conversa, foreign_keys=[conversa_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<DenunciaChat(id={self.id}, denunciante_id={self.denunciante_id}, denunciado_id={self.denunciado_id}, motivo='{self.motivo}')>"
