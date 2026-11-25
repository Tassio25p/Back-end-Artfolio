from app.models.usuario_model import Usuario
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Log(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'log' no PostgreSQL.

    Este modelo mapeia os registros de auditoria do sistema,
    rastreando ações realizadas pelos usuários nas tabelas da aplicação.
    """
    __tablename__ = "log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[Optional[int]] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(50), nullable=False)
    tabelaAfetada: Mapped[str] = mapped_column("tabelaafetada", String(50), nullable=False)
    dataHora: Mapped[Optional[datetime]] = mapped_column("datahora", DateTime, server_default=func.now())
    idRegistroAfetado: Mapped[Optional[int]] = mapped_column("idregistroafetado", nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamento
    usuario: Mapped[Optional[Usuario]] = relationship(Usuario, lazy="joined")

    def __repr__(self) -> str:
        return f"<Log(id={self.id}, acao='{self.acao}', tabelaAfetada='{self.tabelaAfetada}')>"
