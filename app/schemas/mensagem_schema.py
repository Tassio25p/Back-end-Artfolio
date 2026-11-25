from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class MensagemCriar(BaseModel):
    """Schema para envio de uma nova mensagem."""
    conteudo: Optional[str] = Field(None, description="Texto da mensagem")
    arquivoUrl: Optional[str] = Field(None, description="URL de anexo ou imagem")

class ConversaCriar(BaseModel):
    """Schema para criação de conversa direta (1:1) ou em grupo (máx 12 membros)."""
    destinatario_id: Optional[int] = Field(None, description="ID do destinatário para conversa direta 1:1")
    destinatarios_ids: Optional[List[int]] = Field(None, description="Lista de IDs de membros para criação de grupo")
    nome_grupo: Optional[str] = Field(None, max_length=100, description="Nome identificador do grupo")

class MensagemResposta(BaseModel):
    """Schema de resposta para uma mensagem enviada."""
    id: int
    idConversa: int = Field(..., alias="idConversa")
    idRemetente: int = Field(..., alias="idRemetente")
    remetente_nome: Optional[str] = None
    remetente_foto: Optional[str] = None
    conteudo: Optional[str] = None
    arquivoUrl: Optional[str] = Field(None, alias="arquivoUrl")
    dataEnvio: Optional[datetime] = Field(None, alias="dataEnvio")
    deletado: bool = False
    enviado_por_mim: bool = False
    lida: bool = False
    editado_em: Optional[datetime] = Field(None, alias="editado_em")
    deletado_em: Optional[datetime] = Field(None, alias="deletado_em")
    deletado_por_id: Optional[int] = Field(None, alias="deletado_por_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MensagemEditar(BaseModel):
    """Schema para edição de conteúdo de uma mensagem."""
    conteudo: str = Field(..., min_length=1, description="Novo texto da mensagem")

class DenunciaChatCriar(BaseModel):
    """Schema para registrar uma denúncia contra um usuário em uma conversa."""
    denunciado_id: int
    conversa_id: int
    motivo: str = Field(..., min_length=2, max_length=100)
    descricao: Optional[str] = None

class DenunciaChatResposta(BaseModel):
    """Schema de resposta para uma denúncia criada."""
    id: int
    denunciante_id: int
    denunciado_id: int
    conversa_id: int
    motivo: str
    descricao: Optional[str] = None
    status: str = "pendente"
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ConversaUsuarioResposta(BaseModel):
    """Schema do participante da conversa."""
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str = "artista"
    plano: str = "Free"
    mostrar_moldura_led: bool = True
    mostrar_badge_plano: bool = True
    cor_led_hex: Optional[str] = "#E17055"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class GrupoAtualizar(BaseModel):
    """Schema para atualização de dados do grupo pelo admin."""
    nome_grupo: Optional[str] = Field(None, max_length=100, description="Novo nome do grupo")
    foto_grupo: Optional[str] = Field(None, description="URL da foto/ícone do grupo")

class ConversaResposta(BaseModel):
    """Schema de resposta para uma conversa direta ou em grupo."""
    id: int
    is_grupo: bool = False
    nome_grupo: Optional[str] = None
    foto_grupo: Optional[str] = None
    admin_id: Optional[int] = None
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    destinatario: Optional[ConversaUsuarioResposta] = None
    participantes: List[ConversaUsuarioResposta] = []
    ultimaMensagem: Optional[MensagemResposta] = None
    mensagens: List[MensagemResposta] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
