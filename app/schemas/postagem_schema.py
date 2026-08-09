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
    email: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PostagemResposta(BaseModel):
    """
    Schema para expor os dados completos da Obra (Postagem) nas respostas da API.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idCategoria: int = Field(..., alias="idCategoria")
    legenda: Optional[str] = None
    arquivoUrl: str = Field(..., alias="arquivoUrl")
    dataPostagem: Optional[datetime] = Field(None, alias="dataPostagem")
    deletado: bool
    usuario: Optional[PostagemUsuarioResumidoResposta] = None
    categoria: Optional[CategoriaResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PostagemCriar(BaseModel):
    """
    Schema para receber os dados de criação de uma nova Postagem.

    NOTA: O campo idUsuario foi removido. O ID do usuário é obtido
    automaticamente do token JWT para garantir que o artista só possa
    criar postagens em seu próprio nome.
    """
    idCategoria: int = Field(..., description="ID da categoria da obra")
    legenda: Optional[str] = Field(None, description="Legenda ou descrição da obra")
    arquivoUrl: str = Field(..., min_length=1, description="URL do arquivo da obra")

class PostagemAtualizar(BaseModel):
    """
    Schema para receber os dados de atualização de uma Postagem existente.
    Todos os campos são opcionais — somente os informados serão atualizados.
    """
    idCategoria: Optional[int] = Field(None, description="Novo ID da categoria")
    legenda: Optional[str] = Field(None, description="Nova legenda ou descrição")
    arquivoUrl: Optional[str] = Field(None, description="Nova URL do arquivo da obra")


# --- Schemas do Feed ---

class FeedUsuarioResposta(BaseModel):
    """
    Schema resumido do autor da postagem no feed.
    """
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FeedItemResposta(BaseModel):
    """
    Schema de resposta para cada item do feed.

    Contém os dados da postagem, do autor, contagens de likes/comentários/seguidores
    e indicações se o usuário autenticado curtiu e/ou segue o autor.
    """
    id: int
    legenda: Optional[str] = None
    arquivoUrl: str = Field(..., alias="arquivoUrl")
    dataPostagem: Optional[datetime] = Field(None, alias="dataPostagem")
    usuario: FeedUsuarioResposta
    categoria: Optional[CategoriaResposta] = None
    likes: int = 0
    comentarios: int = 0
    seguidores: int = 0
    curtido_por_mim: bool = False
    seguindo_usuario: bool = False
    salvo_por_mim: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FeedResposta(BaseModel):
    """
    Schema de resposta do endpoint de feed.
    """
    items: List[FeedItemResposta]
