from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# --- Schemas de Entrada ---

class AssistenteMensagemEnviar(BaseModel):
    """
    Schema para receber a mensagem enviada pelo usuário ao assistente.
    O campo idConversa é opcional: se omitido, uma nova conversa é criada.
    """
    message: str = Field(..., min_length=1, description="Texto da mensagem do usuário")
    idConversa: Optional[int] = Field(None, description="ID da conversa existente (opcional)")


# --- Schemas de Resposta ---

class AssistenteMensagemResposta(BaseModel):
    """
    Schema de resposta para uma mensagem individual do assistente.
    """
    id: int
    idConversa: int = Field(..., alias="idConversa")
    remetente: str
    mensagem: str
    ferramentaUsada: Optional[str] = Field(None, alias="ferramentaUsada")
    dataEnvio: Optional[datetime] = Field(None, alias="dataEnvio")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AssistenteConversaResposta(BaseModel):
    """
    Schema de resposta para uma conversa completa com histórico de mensagens.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    titulo: Optional[str] = None
    dataInicio: Optional[datetime] = Field(None, alias="dataInicio")
    dataAtualizacao: Optional[datetime] = Field(None, alias="dataAtualizacao")
    ativa: bool
    mensagens: List[AssistenteMensagemResposta] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AssistenteConversaListaResposta(BaseModel):
    """
    Schema resumido para listagem de conversas (sem mensagens).
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    titulo: Optional[str] = None
    dataInicio: Optional[datetime] = Field(None, alias="dataInicio")
    dataAtualizacao: Optional[datetime] = Field(None, alias="dataAtualizacao")
    ativa: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AssistenteEnviarResposta(BaseModel):
    """
    Schema retornado ao frontend após enviar uma mensagem ao assistente.
    Inclui a resposta da IA e o ID da conversa (para mensagens subsequentes).
    """
    idConversa: int
    resposta: str
    mensagemUsuario: AssistenteMensagemResposta
    mensagemAssistente: AssistenteMensagemResposta
