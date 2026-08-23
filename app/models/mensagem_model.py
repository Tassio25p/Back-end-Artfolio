from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Mensagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'mensagem' no PostgreSQL.

    Este modelo mapeia as mensagens enviadas dentro de conversas,
    incluindo conteúdo de texto e/ou arquivo, com controle de deleção lógica (soft delete).

    NOTA: A constraint chk_mensagem_conteudo garante que ao menos um entre
    'conteudo' e 'arquivoUrl' deve ser preenchido.
    """
    __tablename__ = "mensagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idRemetente: Mapped[int] = mapped_column("idremetente", ForeignKey("usuario.id"), nullable=False)
    idConversa: Mapped[int] = mapped_column("idconversa", ForeignKey("conversa.id"), nullable=False)
    conteudo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    arquivoUrl: Mapped[Optional[str]] = mapped_column("arquivourl", String(255), nullable=True)
    dataEnvio: Mapped[Optional[datetime]] = mapped_column("dataenvio", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    deletadoPor: Mapped[Optional[str]] = mapped_column("deletado_por", String(255), default="")
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    remetente: Mapped["Usuario"] = relationship("Usuario", lazy="joined")
    conversa: Mapped["Conversa"] = relationship("Conversa", lazy="joined")

    def __repr__(self) -> str:
        return f"<Mensagem(id={self.id}, idRemetente={self.idRemetente}, idConversa={self.idConversa})>"
