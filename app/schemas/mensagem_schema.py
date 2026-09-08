from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class MensagemCriar(BaseModel):
    """Schema para envio de uma nova mensagem."""
    conteudo: Optional[str] = Field(None, description="Texto da mensagem")
    arquivoUrl: Optional[str] = Field(None, description="URL de anexo ou imagem")

class MensagemResposta(BaseModel):
    """Schema de resposta para uma mensagem enviada."""
    id: int
    idConversa: int = Field(..., alias="idConversa")
    idRemetente: int = Field(..., alias="idRemetente")
    conteudo: Optional[str] = None
    arquivoUrl: Optional[str] = Field(None, alias="arquivoUrl")
    dataEnvio: Optional[datetime] = Field(None, alias="dataEnvio")
    deletado: bool = False
    enviado_por_mim: bool = False
    lida: bool = False
    editado_em: Optional[datetime] = Field(None, alias="editado_em")
    deletado_em: Optional[datetime] = Field(None, alias="deletado_em")
    deletado_por_id: Optional[int] = Field(None, alias="deletado_por_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MensagemEditar(BaseModel):
    """Schema para edição de conteúdo de uma mensagem."""
    conteudo: str = Field(..., min_length=1, description="Novo texto da mensagem")

class DenunciaChatCriar(BaseModel):
    """Schema para registrar uma denúncia contra um usuário em uma conversa."""
    denunciado_id: int
    conversa_id: int
    motivo: str = Field(..., min_length=2, max_length=100)
    descricao: Optional[str] = None

class DenunciaChatResposta(BaseModel):
    """Schema de resposta para uma denúncia criada."""
    id: int
    denunciante_id: int
    denunciado_id: int
    conversa_id: int
    motivo: str
    descricao: Optional[str] = None
    status: str = "pendente"
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ConversaUsuarioResposta(BaseModel):
    """Schema do participante da conversa."""
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str = "artista"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ConversaResposta(BaseModel):
    """Schema de resposta para uma conversa com participante e última mensagem."""
    id: int
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    destinatario: Optional[ConversaUsuarioResposta] = None
    ultimaMensagem: Optional[MensagemResposta] = None
    mensagens: List[MensagemResposta] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
