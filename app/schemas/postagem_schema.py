from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CategoriaResposta(BaseModel):
    """
    Schema de resposta para dados da Categoria.
    """
    id: int
    nomeCategoria: str = Field(..., alias="nomeCategoria")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PostagemUsuarioResumidoResposta(BaseModel):
    """
    Schema resumido do Usuário (Artista/Autor) para resposta aninhada na Postagem.
    """
    id: int
    nome: str
    email: Optional[str] = None
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    foto_perfil: Optional[str] = None
    tipo_conta: str = "artista"
    tipo_usuario: str = "artista"
    plano: Optional[str] = "Free"
    mostrar_moldura_led: bool = True
    total_seguidores: int = 0
    seguidores: int = 0
    usuario_seguindo: bool = False
    seguindo_usuario: bool = False

    @field_validator("total_seguidores", "seguidores", mode="before")
    @classmethod
    def validar_inteiros_usuario(cls, v):
        return 0 if v is None else int(v)

    @field_validator("usuario_seguindo", "seguindo_usuario", mode="before")
    @classmethod
    def validar_booleanos_usuario(cls, v):
        return False if v is None else bool(v)

    @field_validator("mostrar_moldura_led", mode="before")
    @classmethod
    def validar_moldura(cls, v):
        return True if v is None else bool(v)

    @field_validator("plano", mode="before")
    @classmethod
    def validar_plano(cls, v):
        return "Free" if not v else str(v)

    @field_validator("tipo_conta", "tipo_usuario", mode="before")
    @classmethod
    def validar_tipos(cls, v):
        return "artista" if not v else str(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PostagemResposta(BaseModel):
    """
    Schema para expor os dados completos da Obra (Postagem) nas respostas da API.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idCategoria: Optional[int] = Field(None, alias="idCategoria")
    legenda: Optional[str] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    arquivoUrl: str = Field(..., alias="arquivoUrl")
    imagem_url: Optional[str] = None
    arquivos: List[str] = []
    dataPostagem: Optional[datetime] = Field(None, alias="dataPostagem")
    data_criacao: Optional[datetime] = None
    visualizacoes: int = 0
    total_visualizacoes: int = 0
    deletado: bool = False
    usuario: Optional[PostagemUsuarioResumidoResposta] = None
    autor: Optional[PostagemUsuarioResumidoResposta] = None
    categoria: Optional[CategoriaResposta] = None
    categorias: List[CategoriaResposta] = []
    totalCurtidas: int = 0
    total_curtidas: int = 0
    totalComentarios: int = 0
    total_comentarios: int = 0
    totalSalvos: int = 0
    total_salvos: int = 0
    fixado: bool = False
    fixado_em: Optional[datetime] = None
    curtido_por_mim: bool = False
    usuario_curtiu: bool = False
    salvo_por_mim: bool = False
    usuario_salvou: bool = False

    # Recursos Comerciais e Download (Fase 4)
    preco: Optional[Decimal] = None
    a_venda: bool = False
    permite_download: bool = False

    @field_validator("visualizacoes", "total_visualizacoes", "totalCurtidas", "total_curtidas", "totalComentarios", "total_comentarios", "totalSalvos", "total_salvos", mode="before")
    @classmethod
    def validar_inteiros_postagem(cls, v):
        return 0 if v is None else int(v)

    @field_validator("deletado", "fixado", "curtido_por_mim", "usuario_curtiu", "salvo_por_mim", "usuario_salvou", "a_venda", "permite_download", mode="before")
    @classmethod
    def validar_booleanos_postagem(cls, v):
        return False if v is None else bool(v)

    @field_validator("arquivos", "categorias", mode="before")
    @classmethod
    def validar_listas_postagem(cls, v):
        return [] if v is None else v

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PostagemCriar(BaseModel):
    """
    Schema para receber os dados de criação de uma nova Postagem.
    Suporta uma categoria (idCategoria) ou múltiplas (idCategorias ou nomesCategorias).
    Suporta postagem simples (1 imagem) ou carrossel de imagens (arquivos).
    """
    idCategoria: Optional[int] = Field(None, description="ID da categoria principal")
    idCategorias: Optional[List[int]] = Field(None, description="Lista de IDs de categorias da obra")
    nomesCategorias: Optional[List[str]] = Field(None, description="Lista de nomes de categorias caso enviadas pelo nome")
    legenda: Optional[str] = Field(None, description="Legenda ou descrição da obra")
    arquivoUrl: str = Field(..., min_length=1, description="URL do arquivo da obra")
    arquivos: Optional[List[str]] = Field(None, description="Lista de URLs de imagens para carrossel (Pro e Boost)")

    # Recursos Comerciais e Download (Fase 4)
    preco: Optional[Decimal] = Field(None, description="Preço de venda da obra (em R$)")
    a_venda: bool = Field(False, description="Indica se a obra está disponível para venda")
    permite_download: bool = Field(False, description="Indica se o autor permite download livre do arquivo")

    @model_validator(mode="after")
    def validar_recursos_comerciais(self):
        if not self.a_venda:
            self.preco = None
        return self

class PostagemAtualizar(BaseModel):
    """
    Schema para receber os dados de atualização de uma Postagem existente.
    """
    idCategoria: Optional[int] = Field(None, description="Novo ID da categoria")
    idCategorias: Optional[List[int]] = Field(None, description="Nova lista de IDs de categorias")
    nomesCategorias: Optional[List[str]] = Field(None, description="Nova lista de nomes de categorias")
    legenda: Optional[str] = Field(None, description="Nova legenda ou descrição")
    arquivoUrl: Optional[str] = Field(None, description="Nova URL do arquivo da obra")
    arquivos: Optional[List[str]] = Field(None, description="Nova lista de URLs de imagens")

    # Recursos Comerciais e Download (Fase 4)
    preco: Optional[Decimal] = Field(None, description="Novo preço de venda da obra")
    a_venda: Optional[bool] = Field(None, description="Status de venda da obra")
    permite_download: Optional[bool] = Field(None, description="Permissão de download livre")

    @model_validator(mode="after")
    def validar_recursos_comerciais(self):
        if self.a_venda is False:
            self.preco = None
        return self


# --- Schemas do Feed ---

class FeedUsuarioResposta(BaseModel):
    """
    Schema resumido do autor da postagem no feed.
    """
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str = "artista"
    plano: str = "Free"
    mostrar_moldura_led: bool = True

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FeedItemResposta(BaseModel):
    """
    Schema de resposta para cada item do feed.
    """
    id: int
    legenda: Optional[str] = None
    arquivoUrl: str = Field(..., alias="arquivoUrl")
    arquivos: List[str] = []
    dataPostagem: Optional[datetime] = Field(None, alias="dataPostagem")
    usuario: FeedUsuarioResposta
    categoria: Optional[CategoriaResposta] = None
    categorias: List[CategoriaResposta] = []
    likes: int = 0
    comentarios: int = 0
    visualizacoes: int = 0
    seguidores: int = 0
    fixado: bool = False
    fixado_em: Optional[datetime] = None
    curtido_por_mim: bool = False
    seguindo_usuario: bool = False
    salvo_por_mim: bool = False
    destaque_boost: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FeedResposta(BaseModel):
    """
    Schema de resposta do endpoint de feed.
    """
    items: List[FeedItemResposta]
