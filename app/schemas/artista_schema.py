from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class ArtistaResposta(BaseModel):
    """
    Schema para expor os dados de um Artista nas respostas da API.
    """
    id: int
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    biografia: Optional[str] = None
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    portfolio: Optional[str] = None
    tipo_conta: str
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
