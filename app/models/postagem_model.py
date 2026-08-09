from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Postagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'postagem' (Obras) no PostgreSQL.
    """
    __tablename__ = "postagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False)
    idCategoria = Column("idcategoria", Integer, ForeignKey("categoria.id"), nullable=False)
    legenda = Column(Text, nullable=True)
    arquivoUrl = Column("arquivourl", String(255), nullable=False)
    dataPostagem = Column("datapostagem", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos para trazer os dados do Artista/Usuário e da Categoria
    usuario = relationship("Usuario", lazy="joined")
    categoria = relationship("Categoria", lazy="joined")

    def __repr__(self):
        return f"<Postagem(id={self.id}, idUsuario={self.idUsuario}, idCategoria={self.idCategoria})>"
