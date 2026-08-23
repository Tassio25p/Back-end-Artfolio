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
