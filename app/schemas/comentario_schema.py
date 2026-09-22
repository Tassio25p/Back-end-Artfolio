from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ComentarioUsuarioResposta(BaseModel):
    """
    Schema resumido do usuário que fez o comentário.
    """
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ComentarioCriar(BaseModel):
    """
    Schema para criação de um novo comentário.
    """
    conteudo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Conteúdo do comentário (máximo 500 caracteres)",
        json_schema_extra={"example": "Que obra incrível! Adorei o uso das cores."}
    )


class ComentarioResposta(BaseModel):
    """
    Schema de resposta para um comentário, incluindo dados do autor.
    """
    id: int
    conteudo: str
    dataCriacao: datetime = Field(..., alias="dataCriacao")
    usuario: Optional[ComentarioUsuarioResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
