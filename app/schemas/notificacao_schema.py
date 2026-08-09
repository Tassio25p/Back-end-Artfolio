from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class NotificacaoRemetenteResposta(BaseModel):
    """
    Schema resumido do usuário remetente da notificação.
    """
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificacaoResposta(BaseModel):
    """
    Schema para resposta de uma notificação individual.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    tipo: str
    titulo: str
    mensagem: str
    idRemetente: Optional[int] = Field(None, alias="idRemetente")
    idPostagem: Optional[int] = Field(None, alias="idPostagem")
    idComentario: Optional[int] = Field(None, alias="idComentario")
    idConversa: Optional[int] = Field(None, alias="idConversa")
    lida: bool
    dataCriacao: datetime = Field(None, alias="dataCriacao")
    remetente: Optional[NotificacaoRemetenteResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificacaoListResposta(BaseModel):
    """
    Schema para lista de notificações.
    """
    items: List[NotificacaoResposta]


class NotificacaoContadorResposta(BaseModel):
    """
    Schema de resposta para a quantidade de notificações não lidas.
    """
    quantidade: int
