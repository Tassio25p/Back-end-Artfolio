from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class AdminMetricasResposta(BaseModel):
    """
    Métricas do painel administrativo consolidadas em tempo real.
    """
    obras_pendentes: int = Field(..., description="Obras com status 'quarentena' ou 'pendente'")
    denuncias_abertas: int = Field(..., description="Denúncias com status 'pendente'")
    usuarios_sinalizados: int = Field(..., description="Quantidade de usuários denunciados")
    logs_recentes: int = Field(0, description="Total de ações de moderação registradas nos últimos 7 dias")

class JulgarObraRequisicao(BaseModel):
    """
    Requisição para aprovação ou rejeição de uma obra em quarentena.
    """
    acao: str = Field(..., description="'aprovar' ou 'rejeitar'")
    motivo: Optional[str] = Field(None, description="Motivo obrigatório em caso de rejeição")

class SancaoUsuarioRequisicao(BaseModel):
    """
    Requisição para aplicação de sanções administrativas em um usuário.
    """
    acao: str = Field(..., description="'advertir', 'suspender' ou 'banir'")
    dias_suspensao: Optional[int] = Field(None, ge=1, description="Dias de suspensão (obrigatório se acao='suspender')")
    motivo: Optional[str] = Field(None, description="Motivo ou descrição formal da sanção")

class AtualizarDenunciaRequisicao(BaseModel):
    """
    Requisição para resolução ou descarte de uma denúncia.
    """
    status: str = Field(..., description="'resolvida' ou 'descartada'")
    nota_moderador: Optional[str] = Field(None, description="Justificativa ou nota do moderador")

class DenunciaChatResposta(BaseModel):
    id: int
    denunciante_id: int
    denunciante_nome: Optional[str] = None
    denunciante_email: Optional[str] = None
    denunciado_id: int
    denunciado_nome: Optional[str] = None
    denunciado_email: Optional[str] = None
    conversa_id: int
    motivo: str
    descricao: Optional[str] = None
    status: str
    nota_moderador: Optional[str] = None
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class MensagemAuditoriaResposta(BaseModel):
    id: int
    idRemetente: int
    nomeRemetente: Optional[str] = None
    fotoPerfilRemetente: Optional[str] = None
    conteudo: Optional[str] = None
    arquivoUrl: Optional[str] = None
    dataEnvio: Optional[datetime] = None
    foi_apagada: bool = False
    apagado_em: Optional[datetime] = None
    foi_editada: bool = False
    editado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AuditoriaChatResposta(BaseModel):
    denuncia_id: int
    conversa_id: int
    denunciante_id: int
    denunciado_id: int
    motivo: str
    descricao: Optional[str] = None
    mensagens: List[MensagemAuditoriaResposta] = []

class ObraQuarentenaResposta(BaseModel):
    id: int
    idUsuario: int
    artista_nome: Optional[str] = None
    artista_email: Optional[str] = None
    artista_foto: Optional[str] = None
    legenda: Optional[str] = None
    arquivoUrl: str
    arquivos: List[str] = []
    status: str
    dataPostagem: Optional[datetime] = None
    categorias: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class LogAuditoriaResposta(BaseModel):
    id: int
    moderador_id: int
    moderador_nome: Optional[str] = None
    acao: str
    alvo_tipo: str
    alvo_id: int
    detalhes: Optional[str] = None
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UsuarioSinalizadoResposta(BaseModel):
    id: int
    nome: str
    email: Optional[str] = None
    fotoPerfil: Optional[str] = None
    total_denuncias: int = 0
    ativo: bool = True
    suspenso_ate: Optional[datetime] = None
    papel: str = "artista"

    model_config = ConfigDict(from_attributes=True)
