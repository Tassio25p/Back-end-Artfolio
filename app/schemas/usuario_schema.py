import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime

class UsuarioBase(BaseModel):
    """
    Schema base contendo os campos comuns a todas as operações de usuário.
    """
    nome: str = Field(..., min_length=2, max_length=100, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="E-mail único de acesso")
    cpf: Optional[str] = Field(None, description="CPF (11 dígitos) ou CNPJ (14 dígitos)")
    cpf_cnpj: Optional[str] = Field(None, description="CPF ou CNPJ apenas com dígitos")
    tipo_usuario: str = Field("PF", description="Classificação cadastral: 'PF' (Pessoa Física) ou 'PJ' (Pessoa Jurídica)")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone de contato (opcional)")
    biografia: Optional[str] = Field(None, description="Biografia ou apresentação do usuário")
    portfolio: Optional[str] = Field(None, max_length=255, description="Link do portfólio do usuário")
    tipo_conta: str = Field("artista", description="Papel do usuário no sistema (padrão: 'artista')")
    termoAceito: bool = Field(False, description="Indica se o usuário aceitou os Termos e Condições")
    versaoTermo: Optional[str] = Field("v1.0", description="Versão dos Termos aceita")

    @field_validator("tipo_usuario")
    @classmethod
    def validar_tipo_usuario(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ("PF", "PJ"):
            raise ValueError("O tipo de usuário deve ser 'PF' (Pessoa Física) ou 'PJ' (Pessoa Jurídica).")
        return v_upper

    @field_validator("cpf", "cpf_cnpj")
    @classmethod
    def validar_documento(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        somente_numeros = "".join(filter(str.isdigit, v))
        if len(somente_numeros) not in (11, 14):
            raise ValueError("O CPF/CNPJ deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")
        return somente_numeros

    @field_validator("tipo_conta")
    @classmethod
    def validar_tipo_conta(cls, v: str) -> str:
        tipos_validos = ["artista", "cliente", "moderador", "admin", "visitante"]
        v_lowered = v.lower()
        if v_lowered not in tipos_validos:
            raise ValueError(f"Tipo de conta inválido. Deve ser um dos seguintes: {', '.join(tipos_validos)}.")
        return v_lowered

class UsuarioCadastro(UsuarioBase):
    """
    Esquema para requisição de cadastro de um novo usuário / artista.
    Exige a senha em texto puro e a confirmação dos termos.
    """
    senha: str = Field(..., min_length=6, max_length=100, description="Senha de acesso (mínimo de 6 caracteres)")
    termoAceito: bool = Field(..., description="Aceite obrigatório dos Termos de Uso e Política de Privacidade")

    @field_validator("termoAceito")
    @classmethod
    def validar_aceite_termos(cls, v: bool) -> bool:
        if not v:
            raise ValueError("É necessário que haja a aceitação dos Termos e Condições para fazer uso da plataforma.")
        return v

class UsuarioLogin(BaseModel):
    """
    Esquema para requisição de login.
    """
    email: EmailStr = Field(..., description="E-mail cadastrado")
    senha: str = Field(..., description="Senha de acesso")

class GoogleLoginSchema(BaseModel):
    """
    Schema para requisição de login/cadastro via Google.
    """
    token: str = Field(..., description="ID Token do Google enviado pelo frontend")

class UsuarioUpdateSchema(BaseModel):
    """
    Schema para atualização parcial do perfil do usuário autenticado.
    """
    nome: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Nome completo do usuário"
    )
    telefone: Optional[str] = Field(
        None,
        max_length=20,
        description="Telefone de contato com DDD"
    )
    biografia: Optional[str] = Field(
        None,
        max_length=1000,
        description="Biografia ou apresentação do usuário"
    )
    portfolio: Optional[str] = Field(
        None,
        max_length=255,
        description="Link do portfólio do usuário"
    )
    instagram: Optional[str] = Field(
        None,
        max_length=255,
        description="Usuário do Instagram"
    )
    behance: Optional[str] = Field(
        None,
        max_length=255,
        description="Usuário do Behance"
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="URL do site pessoal do usuário"
    )
    trajetoria: Optional[str] = Field(
        None,
        description="Trajetória artística e experiências profissionais"
    )
    especializacoes: Optional[str] = Field(
        None,
        description="Especializações e técnicas artísticas"
    )
    certificados: Optional[str] = Field(
        None,
        description="Certificados, qualificações e documentos (JSON estruturado)"
    )

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        somente_numeros = "".join(filter(str.isdigit, v))
        if len(somente_numeros) < 10 or len(somente_numeros) > 11:
            raise ValueError("O telefone deve conter entre 10 e 11 dígitos numéricos.")
        return v

    @field_validator("instagram")
    @classmethod
    def validar_instagram(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        padrao_url = re.compile(
            r"^(?:https?://)?(?:www\.)?instagram\.com/(.+?)/?$", re.IGNORECASE
        )
        match = padrao_url.match(v)
        if match:
            return match.group(1)
        if "/" in v or " " in v:
            raise ValueError("Instagram inválido. Informe o usuário (ex: 'joaosilva') ou a URL.")
        return v

    @field_validator("behance")
    @classmethod
    def validar_behance(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        padrao_url = re.compile(
            r"^(?:https?://)?(?:www\.)?behance\.net/(.+?)/?$", re.IGNORECASE
        )
        match = padrao_url.match(v)
        if match:
            return match.group(1)
        if "/" in v or " " in v:
            raise ValueError("Behance inválido. Informe o usuário (ex: 'joaosilva') ou a URL.")
        return v

    @field_validator("website")
    @classmethod
    def validar_website(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        padrao_url = re.compile(
            r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE
        )
        if not padrao_url.match(v):
            raise ValueError("URL do website inválida. Deve começar com http:// ou https://.")
        return v

class UsuarioSenhaSchema(BaseModel):
    """
    Schema para alteração de senha do usuário autenticado.
    """
    senhaAtual: str = Field(..., description="Senha atual do usuário")
    novaSenha: str = Field(..., min_length=6, max_length=100, description="Nova senha desejada")
    confirmacaoSenha: str = Field(..., description="Confirmação da nova senha")

    @model_validator(mode="after")
    def validar_confirmacao_senha(self) -> "UsuarioSenhaSchema":
        if self.novaSenha != self.confirmacaoSenha:
            raise ValueError("A nova senha e a confirmação não coincidem.")
        return self

class UsuarioResposta(BaseModel):
    """
    Esquema para expor os dados do usuário nas respostas da API.
    """
    id: int
    nome: str
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    tipo_usuario: Optional[str] = "PF"
    telefone: Optional[str] = None
    biografia: Optional[str] = None
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    portfolio: Optional[str] = None
    instagram: Optional[str] = None
    behance: Optional[str] = None
    website: Optional[str] = None
    trajetoria: Optional[str] = None
    especializacoes: Optional[str] = None
    certificados: Optional[str] = None
    tipo_conta: str = "artista"
    termoAceito: Optional[bool] = True
    dataAceiteTermo: Optional[datetime] = None
    versaoTermo: Optional[str] = "v1.0"
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    deletado: bool = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class TokenResposta(BaseModel):
    """
    Esquema retornado ao efetuar login com sucesso.
    """
    token_acesso: str = Field(..., alias="access_token")
    tipo_token: str = Field("bearer", alias="token_type")
    usuario: UsuarioResposta

    model_config = ConfigDict(populate_by_name=True)

from app.schemas.seguidor_schema import RelacionamentoStatusResposta

class PerfilPublicoResposta(BaseModel):
    """
    Schema para dados públicos completos do perfil de um usuário.
    """
    id: int
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    biografia: Optional[str] = None
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    portfolio: Optional[str] = None
    instagram: Optional[str] = None
    behance: Optional[str] = None
    website: Optional[str] = None
    trajetoria: Optional[str] = None
    especializacoes: Optional[str] = None
    certificados: Optional[str] = None
    tipo_conta: str = "artista"
    tipo_usuario: Optional[str] = "PF"
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    
    seguidoresCount: int = 0
    seguindoCount: int = 0
    obrasCount: int = 0
    curtidasTotais: int = 0
    visualizacoesTotais: int = 0
    relacionamento: RelacionamentoStatusResposta = Field(default_factory=RelacionamentoStatusResposta)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
