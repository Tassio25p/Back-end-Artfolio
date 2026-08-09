from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, func
from app.database import Base


class Seguidor(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'seguidor' no PostgreSQL.

    Armazena o relacionamento de seguir entre usuários.
    Possui uma constraint UNIQUE para evitar que um usuário
    siga outro mais de uma vez.
    """
    __tablename__ = "seguidor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idSeguidor = Column("idseguidor", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    idSeguido = Column("idseguido", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idseguidor", "idseguido", name="uq_seguidor_seguido"),
    )

    def __repr__(self):
        return f"<Seguidor(id={self.id}, idSeguidor={self.idSeguidor}, idSeguido={self.idSeguido})>"
