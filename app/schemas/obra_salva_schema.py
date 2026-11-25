from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.postagem_schema import PostagemResposta


class ObraSalvaResposta(BaseModel):
    """
    Schema de resposta para uma obra salva.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idPostagem: int = Field(..., alias="idPostagem")
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    postagem: Optional[PostagemResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SalvarStatusResposta(BaseModel):
    """
    Schema simples de resposta para status de salvamento de uma obra.
    """
    message: str
    salvo: bool
