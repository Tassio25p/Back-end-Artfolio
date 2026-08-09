from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class Categoria(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'categoria' no PostgreSQL.
    """
    __tablename__ = "categoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nomeCategoria = Column("nomecategoria", String(50), unique=True, nullable=False)
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    def __repr__(self):
        return f"<Categoria(id={self.id}, nomeCategoria='{self.nomeCategoria}')>"
