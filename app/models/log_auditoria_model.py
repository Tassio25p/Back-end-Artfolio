from app.models.usuario_model import Usuario
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class LogAuditoria(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'logs_auditoria'.
    Registra todas as ações administrativas e de moderação realizadas na plataforma.
    """
    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    moderador_id: Mapped[int] = mapped_column("moderador_id", ForeignKey("usuario.id"), nullable=False, index=True)
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    alvo_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    alvo_id: Mapped[int] = mapped_column(nullable=False)
    detalhes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[Optional[datetime]] = mapped_column("criado_em", DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    # Relacionamento com o usuário moderador
    moderador: Mapped[Usuario] = relationship(Usuario, foreign_keys=[moderador_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<LogAuditoria(id={self.id}, moderador_id={self.moderador_id}, acao='{self.acao}', alvo_tipo='{self.alvo_tipo}', alvo_id={self.alvo_id})>"
