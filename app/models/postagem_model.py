from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Postagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'postagem' (Obras) no PostgreSQL normalizado.
    O relacionamento com Categorias é exclusivamente N:N através de 'postagem_categoria'.
    """
    __tablename__ = "postagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False)
    legenda: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    arquivoUrl: Mapped[str] = mapped_column("arquivourl", String(255), nullable=False)
    arquivos_raw: Mapped[Optional[str]] = mapped_column("arquivos", Text, nullable=True)
    visualizacoes: Mapped[int] = mapped_column(BigInteger, default=0)
    dataPostagem: Mapped[Optional[datetime]] = mapped_column("datapostagem", DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="publicada")  # 'publicada', 'quarentena', 'pendente', 'rejeitada'
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Relacionamento com o autor da obra
    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="joined")
    
    # Relação N:N com categorias via tabela intermediária postagem_categoria
    postagem_categorias: Mapped[List["PostagemCategoria"]] = relationship(
        "PostagemCategoria",
        back_populates="postagem",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    @property
    def categorias(self) -> List["Categoria"]:
        """Retorna lista de todas as categorias associadas via N:N."""
        return [pc.categoria for pc in self.postagem_categorias if pc.categoria and not pc.categoria.deletado]

    @property
    def categoria(self) -> Optional["Categoria"]:
        """Retorna a categoria principal (primeira vinculada) para compatibilidade."""
        cats = self.categorias
        return cats[0] if cats else None

    @property
    def idCategoria(self) -> Optional[int]:
        """Retorna o ID da categoria principal para compatibilidade."""
        cat = self.categoria
        return cat.id if cat else None

    @property
    def lista_arquivos(self) -> List[str]:
        """Retorna lista de URLs de arquivos da postagem para suporte a carrossel."""
        if self.arquivos_raw:
            try:
                import json
                parsed = json.loads(self.arquivos_raw)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [a.strip() for a in self.arquivos_raw.split(",") if a.strip()]
        return [self.arquivoUrl] if self.arquivoUrl else []

    @property
    def arquivos(self) -> List[str]:
        """Property para Pydantic PostagemResposta carregar o carrossel."""
        return self.lista_arquivos

    def __repr__(self) -> str:
        return f"<Postagem(id={self.id}, idUsuario={self.idUsuario})>"
