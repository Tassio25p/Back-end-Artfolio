from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, func
from app.database import Base


class Curtida(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'curtida' no PostgreSQL.

    Armazena as curtidas (likes) dos usuários nas postagens.
    Possui uma constraint UNIQUE para evitar curtidas duplicadas
    do mesmo usuário na mesma postagem.
    """
    __tablename__ = "curtida"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    idPostagem = Column("idpostagem", Integer, ForeignKey("postagem.id"), nullable=False, index=True)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idusuario", "idpostagem", name="uq_curtida_usuario_postagem"),
    )

    def __repr__(self):
        return f"<Curtida(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem})>"
