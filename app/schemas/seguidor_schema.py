from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class SeguidorResposta(BaseModel):
    """
    Schema de resposta para um relacionamento de seguir.
    """
    id: int
    idSeguidor: int = Field(..., alias="idSeguidor")
    idSeguido: int = Field(..., alias="idSeguido")
    dataCriacao: datetime = Field(None, alias="dataCriacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
