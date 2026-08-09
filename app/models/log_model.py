from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Log(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'log' no PostgreSQL.

    Este modelo mapeia os registros de auditoria do sistema,
    rastreando ações realizadas pelos usuários nas tabelas da aplicação.
    """
    __tablename__ = "log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=True)
    acao = Column(String(50), nullable=False)
    tabelaAfetada = Column("tabelaafetada", String(50), nullable=False)
    dataHora = Column("datahora", DateTime, server_default=func.now())
    idRegistroAfetado = Column("idregistroafetado", Integer, nullable=True)
    descricao = Column(Text, nullable=True)

    # Relacionamento
    usuario = relationship("Usuario", lazy="joined")

    def __repr__(self):
        return f"<Log(id={self.id}, acao='{self.acao}', tabelaAfetada='{self.tabelaAfetada}')>"
