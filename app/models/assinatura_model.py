from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False)
    idPlano = Column("idplano", Integer, ForeignKey("plano.id"), nullable=False)
    dataInicio = Column("datainicio", DateTime, server_default=func.now())
    dataFim = Column("datafim", DateTime, nullable=True)
    ativa = Column(Boolean, default=True)
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    usuario = relationship("Usuario", lazy="joined")
    plano = relationship("Plano", lazy="joined")

    def __repr__(self):
        return f"<Assinatura(id={self.id}, idUsuario={self.idUsuario}, idPlano={self.idPlano}, ativa={self.ativa})>"
