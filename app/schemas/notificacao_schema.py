from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
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
    Schema padronizado para resposta de uma notificação individual,
    suportando tanto a nomenclatura padronizada da Fase 3 quanto os campos legados.
    """
    id: int
    usuario_id: int
    tipo: str
    titulo: str
    conteudo: str
    referencia_id: Optional[int] = None
    link_acao: Optional[str] = None
    lida: bool = False
    criado_em: Optional[datetime] = None

    # Campos de compatibilidade com o frontend e endpoints legados
    idUsuario: Optional[int] = None
    mensagem: Optional[str] = None
    dataCriacao: Optional[datetime] = None
    idRemetente: Optional[int] = None
    idPostagem: Optional[int] = None
    idComentario: Optional[int] = None
    idConversa: Optional[int] = None
    remetente: Optional[NotificacaoRemetenteResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Alias para o schema de item individual
NotificacaoItem = NotificacaoResposta


class NotificacoesPaginadasResposta(BaseModel):
    """
    Schema padronizado para o retorno paginado de GET /notificacoes.
    """
    total_nao_lidas: int
    total: int
    notificacoes: List[NotificacaoResposta]
    items: Optional[List[NotificacaoResposta]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificacaoListResposta(BaseModel):
    """
    Schema legado para compatibilidade com rotas que retornam {'items': [...]}.
    """
    items: List[NotificacaoResposta]
    total_nao_lidas: Optional[int] = None
    total: Optional[int] = None
    notificacoes: Optional[List[NotificacaoResposta]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificacaoContadorResposta(BaseModel):
    """
    Schema de resposta para a quantidade de notificações não lidas.
    """
    quantidade: int


class NotificacaoAcaoLoteResposta(BaseModel):
    """
    Schema de resposta para operações em lote (ex: PATCH /notificacoes/ler-todas).
    """
    status: str = "sucesso"
    total_atualizadas: int
    atualizadas: Optional[int] = None
    message: Optional[str] = None


class NotificacaoAcaoResposta(BaseModel):
    """
    Schema de resposta para operações individuais (ex: DELETE /notificacoes/{id}).
    """
    status: str = "sucesso"
    mensagem: str
