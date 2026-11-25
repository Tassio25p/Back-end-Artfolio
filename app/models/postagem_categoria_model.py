from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from typing import Optional
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PostagemCategoria(Base):
    """
    Modelo SQLAlchemy que representa a tabela intermediária 'postagem_categoria' (N:N) no PostgreSQL.
    Possui chave primária composta (idpostagem, idcategoria).
    """
    __tablename__ = "postagem_categoria"

    idPostagem: Mapped[int] = mapped_column("idpostagem", ForeignKey("postagem.id", ondelete="CASCADE"), primary_key=True)
    idCategoria: Mapped[int] = mapped_column("idcategoria", ForeignKey("categoria.id", ondelete="CASCADE"), primary_key=True)

    # Relacionamentos
    postagem: Mapped[Postagem] = relationship(Postagem, back_populates="postagem_categorias", foreign_keys=[idPostagem])
    categoria: Mapped[Categoria] = relationship(Categoria, foreign_keys=[idCategoria], lazy="joined")

    def __repr__(self) -> str:
        return f"<PostagemCategoria(idPostagem={self.idPostagem}, idCategoria={self.idCategoria})>"
