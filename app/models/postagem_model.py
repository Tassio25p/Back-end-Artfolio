from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import BigInteger, String, Text, Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.categoria_model import Categoria
    from app.models.usuario_model import Usuario
    from app.models.postagem_categoria_model import PostagemCategoria

class Postagem(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'postagem' (Obras) no PostgreSQL normalizado.
    O relacionamento com Categorias é exclusivamente N:N através de 'postagem_categoria'.
    """
    __tablename__ = "postagem"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    idUsuario: Mapped[int] = mapped_column("idusuario", ForeignKey("usuario.id"), nullable=False)
    legenda: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    arquivoUrl: Mapped[str] = mapped_column("arquivourl", String(255), nullable=False)
    arquivos_raw: Mapped[Optional[str]] = mapped_column("arquivos", Text, nullable=True)
    visualizacoes: Mapped[int] = mapped_column(BigInteger, default=0)
    dataPostagem: Mapped[Optional[datetime]] = mapped_column("datapostagem", DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="publicada")  # 'publicada', 'quarentena', 'pendente', 'rejeitada'
    fixado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fixado_em: Mapped[Optional[datetime]] = mapped_column("fixado_em", DateTime, nullable=True)
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)

    # Recursos Comerciais e Download (Fase 4)
    preco: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True, default=None)
    a_venda: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permite_download: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relacionamento com o autor da obra
    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="joined")
    
    # Relação N:N com categorias via tabela intermediária postagem_categoria
    postagem_categorias: Mapped[List["PostagemCategoria"]] = relationship(
        "PostagemCategoria",
        back_populates="postagem",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # Atributos dinâmicos / calculados para serialização e respostas da API
    totalCurtidas: Optional[int] = None
    total_curtidas: Optional[int] = None
    totalComentarios: Optional[int] = None
    total_comentarios: Optional[int] = None
    totalSalvos: Optional[int] = None
    total_salvos: Optional[int] = None
    total_visualizacoes: Optional[int] = None
    curtido_por_mim: Optional[bool] = None
    usuario_curtiu: Optional[bool] = None
    salvo_por_mim: Optional[bool] = None
    usuario_salvou: Optional[bool] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    imagem_url: Optional[str] = None
    data_criacao: Optional[datetime] = None
    autor: Optional[Any] = None

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
