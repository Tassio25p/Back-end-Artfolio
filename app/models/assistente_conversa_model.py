from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class AssistenteConversa(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'assistente_conversa' no PostgreSQL.

    Este modelo mapeia as conversas entre um usuário e o assistente de IA,
    incluindo controle de deleção lógica (soft delete) e estado ativo/inativo.
    """
    __tablename__ = "assistente_conversa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False)
    titulo = Column(String(150), nullable=True)
    dataInicio = Column("datainicio", DateTime, server_default=func.now())
    dataAtualizacao = Column("dataatualizacao", DateTime, server_default=func.now(), onupdate=func.now())
    ativa = Column(Boolean, default=True)
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    usuario = relationship("Usuario", lazy="joined")
    mensagens = relationship("AssistenteMensagem", back_populates="conversa", lazy="joined", order_by="AssistenteMensagem.dataEnvio")

    def __repr__(self):
        return f"<AssistenteConversa(id={self.id}, idUsuario={self.idUsuario}, titulo='{self.titulo}')>"
