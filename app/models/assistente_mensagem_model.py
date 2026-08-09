from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AssistenteMensagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'assistente_mensagem' no PostgreSQL.

    Este modelo mapeia as mensagens trocadas entre o usuário e o assistente de IA
    dentro de uma conversa, incluindo metadados da ferramenta usada e a resposta
    JSON bruta do agente.
    """
    __tablename__ = "assistente_mensagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idConversa = Column("idconversa", Integer, ForeignKey("assistente_conversa.id"), nullable=False)
    remetente = Column(String(20), nullable=False)  # 'usuario' ou 'assistente'
    mensagem = Column(Text, nullable=False)
    ferramentaUsada = Column("ferramentausada", String(100), nullable=True)
    respostaJson = Column("respostajson", JSONB, nullable=True)
    dataEnvio = Column("dataenvio", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos
    conversa = relationship("AssistenteConversa", back_populates="mensagens")

    def __repr__(self):
        return f"<AssistenteMensagem(id={self.id}, idConversa={self.idConversa}, remetente='{self.remetente}')>"
