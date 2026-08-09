from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Comentario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'comentario' no PostgreSQL.

    Armazena os comentários dos usuários nas postagens.
    Utiliza soft delete seguindo o padrão do projeto.
    """
    __tablename__ = "comentario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    idPostagem = Column("idpostagem", Integer, ForeignKey("postagem.id"), nullable=False, index=True)
    conteudo = Column(Text, nullable=False)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamento para trazer os dados do usuário que comentou
    usuario = relationship("Usuario", lazy="joined")

    def __repr__(self):
        return f"<Comentario(id={self.id}, idUsuario={self.idUsuario}, idPostagem={self.idPostagem})>"
