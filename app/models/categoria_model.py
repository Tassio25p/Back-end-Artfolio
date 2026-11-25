from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Categoria(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'categoria' no PostgreSQL.
    Suporta categorias normais e temas rotativos de 'Desafios Semanais' (Art Prompts).
    """
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nomeCategoria: Mapped[str] = mapped_column("nomecategoria", String(50), unique=True, nullable=False)
    is_desafio: Mapped[bool] = mapped_column("is_desafio", Boolean, default=False, server_default=text("false"), nullable=False)
    desafio_ativo: Mapped[bool] = mapped_column("desafio_ativo", Boolean, default=False, server_default=text("false"), nullable=False)
    data_inicio_desafio: Mapped[datetime | None] = mapped_column("data_inicio_desafio", DateTime, nullable=True)
    prazo_dias: Mapped[int] = mapped_column("prazo_dias", Integer, default=7, server_default=text("7"), nullable=False)
    data_fim_desafio: Mapped[datetime | None] = mapped_column("data_fim_desafio", DateTime, nullable=True)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    dataDelecao: Mapped[datetime | None] = mapped_column("datadelecao", DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Categoria(id={self.id}, nomeCategoria='{self.nomeCategoria}', is_desafio={self.is_desafio}, desafio_ativo={self.desafio_ativo})>"
