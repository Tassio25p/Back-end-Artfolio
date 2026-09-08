from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

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
    curtido_por_mim: bool = False
    usuario_curtiu: bool = False
    salvo_por_mim: bool = False
    usuario_salvou: bool = False

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

class PostagemAtualizar(BaseModel):
    """
    Schema para receber os dados de atualização de uma Postagem existente.
    """
    idCategoria: Optional[int] = Field(None, description="Novo ID da categoria")
    idCategorias: Optional[List[int]] = Field(None, description="Nova lista de IDs de categorias")
    legenda: Optional[str] = Field(None, description="Nova legenda ou descrição")
    arquivoUrl: Optional[str] = Field(None, description="Nova URL do arquivo da obra")
    arquivos: Optional[List[str]] = Field(None, description="Nova lista de URLs de imagens")


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
    curtido_por_mim: bool = False
    seguindo_usuario: bool = False
    salvo_por_mim: bool = False
    destaque_boost: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FeedResposta(BaseModel):
    """
    Schema de resposta do endpoint de feed.
    """
    items: List[FeedItemResposta]
