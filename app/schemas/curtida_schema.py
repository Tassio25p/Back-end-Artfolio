from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class CurtidaResposta(BaseModel):
    """
    Schema de resposta para uma curtida (tabela associativa com chave composta idUsuario, idPostagem).
    """
    idUsuario: int = Field(..., alias="idUsuario")
    idPostagem: int = Field(..., alias="idPostagem")
    dataCurtida: Optional[datetime] = Field(None, alias="dataCurtida")
    curtido: bool = True

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
