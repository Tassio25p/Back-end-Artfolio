from sqlalchemy import Column, Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ObraSalva(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'obra_salva' no PostgreSQL.

    Armazena os registros de obras/postagens salvas pelos usuários.
    Garante que o mesmo usuário não possa salvar a mesma postagem mais de uma vez.
    """
    __tablename__ = "obra_salva"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    idPostagem = Column("idpostagem", Integer, ForeignKey("postagem.id"), nullable=False, index=True)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idusuario", "idpostagem", name="uq_obra_salva_usuario_postagem"),
    )

    usuario = relationship("Usuario", lazy="joined")
    postagem = relationship("Postagem", lazy="joined")

    def __repr__(self):
        return f"<ObraSalva(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem})>"
