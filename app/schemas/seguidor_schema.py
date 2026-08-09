from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SeguidorResposta(BaseModel):
    """
    Schema de resposta para um relacionamento de seguir.
    """
    id: int
    idSeguidor: int = Field(..., alias="idSeguidor")
    idSeguido: int = Field(..., alias="idSeguido")
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RelacionamentoStatusResposta(BaseModel):
    """
    Schema detalhado sobre o status de relacionamento entre o usuário logado e o usuário alvo.
    """
    seguindo: bool = False
    segueDeVolta: bool = False
    isMe: bool = False
    seguidoresCount: int = 0
    seguindoCount: int = 0


class UsuarioRelacionamentoItem(BaseModel):
    """
    Schema representando um usuário na lista de seguidores/seguindo com flags de relacionamento.
    """
    id: int
    nome: str
    email: str
    fotoPerfil: Optional[str] = None
    tipo_conta: str = "cliente"
    biografia: Optional[str] = None
    seguindo: bool = False
    segueDeVolta: bool = False
    isMe: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

