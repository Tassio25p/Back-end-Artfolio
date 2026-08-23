from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Notificacao(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'notificacao' no PostgreSQL.

    Armazena as notificações enviadas aos usuários sobre interações
    como curtidas, comentários, seguidores e mensagens.
    Utiliza soft delete seguindo o padrão do projeto.
    """
    __tablename__ = "notificacao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # 'LIKE', 'FOLLOW', 'COMMENT', 'MESSAGE'
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    idRemetente: Mapped[Optional[int]] = mapped_column("idremetente", ForeignKey("usuario.id"), nullable=True)
    idPostagem: Mapped[Optional[int]] = mapped_column("idpostagem", ForeignKey("postagem.id"), nullable=True)
    idComentario: Mapped[Optional[int]] = mapped_column("idcomentario", ForeignKey("comentario.id"), nullable=True)
    idConversa: Mapped[Optional[int]] = mapped_column("idconversa", ForeignKey("conversa.id"), nullable=True)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamentos para carregar dados do destinatário, remetente e postagem
    usuario: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[idUsuario], lazy="joined")
    remetente: Mapped[Optional["Usuario"]] = relationship("Usuario", foreign_keys=[idRemetente], lazy="joined")
    postagem: Mapped[Optional["Postagem"]] = relationship("Postagem", foreign_keys=[idPostagem], lazy="joined")

    def __repr__(self) -> str:
        return f"<Notificacao(id={self.id}, idUsuario={self.idUsuario}, tipo='{self.tipo}', lida={self.lida})>"
