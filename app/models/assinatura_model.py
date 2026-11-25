from app.models.plano_model import Plano
from app.models.usuario_model import Usuario
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Assinatura(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'assinatura' no PostgreSQL.

    Este modelo mapeia as assinaturas de planos dos usuários,
    incluindo período de validade e controle de deleção lógica (soft delete).

    NOTA: A constraint chk_periodo_assinatura garante que dataFim >= dataInicio
    quando dataFim não for nula.
    """
    __tablename__ = "assinatura"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False)
    idPlano: Mapped[int] = mapped_column("idplano", ForeignKey("plano.id"), nullable=False)
    dataInicio: Mapped[Optional[datetime]] = mapped_column("datainicio", DateTime, server_default=func.now())
    dataFim: Mapped[Optional[datetime]] = mapped_column("datafim", DateTime, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    usuario: Mapped[Usuario] = relationship(Usuario, lazy="joined")
    plano: Mapped[Plano] = relationship(Plano, lazy="joined")

    def __repr__(self) -> str:
        return f"<Assinatura(id={self.id}, idUsuario={self.idUsuario}, idPlano={self.idPlano}, ativa={self.ativa})>"
