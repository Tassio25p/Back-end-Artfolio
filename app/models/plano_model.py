from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric
from app.database import Base

class Plano(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'plano' no PostgreSQL.

    Este modelo mapeia os planos de assinatura disponíveis na plataforma,
    incluindo tipo, descrição e controle de ativação e deleção lógica (soft delete).
    """
    __tablename__ = "plano"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isAtivo = Column("isativo", Boolean, default=True)
    tipo = Column(String(100), nullable=False)
    precoPlano = Column("precoplano", Numeric(10, 2), nullable=True)
    descricao = Column(Text, nullable=True)
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    def __repr__(self):
        return f"<Plano(id={self.id}, tipo='{self.tipo}', precoPlano={self.precoPlano}, isAtivo={self.isAtivo})>"
