from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Mensagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'mensagem' no PostgreSQL.

    Este modelo mapeia as mensagens enviadas dentro de conversas,
    incluindo conteúdo de texto e/ou arquivo, com controle de deleção lógica (soft delete).

    NOTA: A constraint chk_mensagem_conteudo garante que ao menos um entre
    'conteudo' e 'arquivoUrl' deve ser preenchido.
    """
    __tablename__ = "mensagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idRemetente = Column("idremetente", Integer, ForeignKey("usuario.id"), nullable=False)
    idConversa = Column("idconversa", Integer, ForeignKey("conversa.id"), nullable=False)
    conteudo = Column(Text, nullable=True)
    arquivoUrl = Column("arquivourl", String(255), nullable=True)
    dataEnvio = Column("dataenvio", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    remetente = relationship("Usuario", lazy="joined")
    conversa = relationship("Conversa", lazy="joined")

    def __repr__(self):
        return f"<Mensagem(id={self.id}, idRemetente={self.idRemetente}, idConversa={self.idConversa})>"
