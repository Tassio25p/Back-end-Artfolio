from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class ConversaUsuario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'conversausuario' no PostgreSQL.

    Este modelo mapeia a tabela associativa (N:N) entre conversas e usuários,
    utilizando chave primária composta (idConversa, idUsuario).
    """
    __tablename__ = "conversausuario"

    idConversa = Column("idconversa", Integer, ForeignKey("conversa.id"), primary_key=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), primary_key=True)
    dataEntrada = Column("dataentrada", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    conversa = relationship("Conversa", lazy="joined")
    usuario = relationship("Usuario", lazy="joined")

    def __repr__(self):
        return f"<ConversaUsuario(idConversa={self.idConversa}, idUsuario={self.idUsuario})>"
