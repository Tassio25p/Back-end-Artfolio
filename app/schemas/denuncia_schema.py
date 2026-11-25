from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.usuario_schema import UsuarioResposta
from app.schemas.postagem_schema import PostagemResposta


class DenunciaCriar(BaseModel):
    """
    Schema para recebimento de requisição de denúncia de uma obra.
    """
    motivo: str = Field(..., min_length=1, max_length=100, description="Motivo da denúncia")
    descricao: Optional[str] = Field(None, max_length=1000, description="Descrição detalhada opcional")


class DenunciaResposta(BaseModel):
    """
    Schema de resposta para uma denúncia registrada.
    """
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idPostagem: int = Field(..., alias="idPostagem")
    motivo: str
    descricao: Optional[str] = None
    status: str
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    usuario: Optional[UsuarioResposta] = None
    postagem: Optional[PostagemResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DenunciaAtualizarStatus(BaseModel):
    """
    Schema para atualização do status de uma denúncia pelo admin/moderador.
    """
    status: str = Field(..., description="Novo status ('PENDENTE', 'EM_ANALISE', 'RESOLVIDA', 'REJEITADA')")
