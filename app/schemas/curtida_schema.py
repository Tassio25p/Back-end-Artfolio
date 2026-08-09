from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class CurtidaResposta(BaseModel):
    """
    Schema de resposta para uma curtida.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idPostagem: int = Field(..., alias="idPostagem")
    dataCriacao: datetime = Field(None, alias="dataCriacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
