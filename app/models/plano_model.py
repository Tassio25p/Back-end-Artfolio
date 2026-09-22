from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plano(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'plano' no PostgreSQL.

    Este modelo mapeia os planos de assinatura disponíveis na plataforma,
    incluindo tipo, descrição e controle de ativação e deleção lógica (soft delete).
    """
    __tablename__ = "plano"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    isAtivo: Mapped[bool] = mapped_column("isativo", Boolean, default=True)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    precoPlano: Mapped[Decimal | None] = mapped_column("precoplano", Numeric(10, 2), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[datetime | None] = mapped_column("datadelecao", DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Plano(id={self.id}, tipo='{self.tipo}', precoPlano={self.precoPlano}, isAtivo={self.isAtivo})>"
