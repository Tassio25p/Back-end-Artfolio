from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class PostagemVisualizacao(Base):
    """
    Modelo SQLAlchemy que armazena visualizações únicas por usuário/postagem
    para impedir contagens repetidas (farming de visualizações).
    """
    __tablename__ = "postagem_visualizacao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idPostagem: Mapped[int] = mapped_column("idpostagem", ForeignKey("postagem.id", ondelete="CASCADE"), nullable=False, index=True)
    idUsuario: Mapped[Optional[int]] = mapped_column("idusuario", ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True, index=True)
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idpostagem", "idusuario", name="uq_postagem_usuario_view"),
    )
