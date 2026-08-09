from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Denuncia(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'denuncia' no PostgreSQL.

    Armazena as denúncias enviadas pelos usuários sobre obras/postagens.
    """
    __tablename__ = "denuncia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False, index=True) # Denunciante
    idPostagem = Column("idpostagem", Integer, ForeignKey("postagem.id"), nullable=False, index=True) # Obra denunciada
    motivo = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    status = Column(String(20), default="PENDENTE") # PENDENTE, EM_ANALISE, RESOLVIDA, REJEITADA
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("idusuario", "idpostagem", name="uq_denuncia_usuario_postagem"),
    )

    usuario = relationship("Usuario", lazy="joined")
    postagem = relationship("Postagem", lazy="joined")

    def __repr__(self):
        return f"<Denuncia(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem}, motivo='{self.motivo}')>"
