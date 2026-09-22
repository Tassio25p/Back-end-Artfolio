from app.schemas.seguidor_schema import RelacionamentoStatusResposta
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
    mostrar_moldura_led: Optional[bool] = Field(
        None,
        description="Ativar ou desativar a moldura de LED do plano ao redor do avatar"
    )
    mostrar_badge_plano: Optional[bool] = Field(
        None,
        description="Ativar ou desativar a exibição do selo do plano no perfil público"
    )
    cor_led_hex: Optional[str] = Field(
        None,
        description="Cor personalizada em HEX para o LED do avatar (exclusivo Boost)"
    )
    mensagem_cta: Optional[str] = Field(
        None,
        max_length=500,
        description="Mensagem padrão de encomenda/orçamento que abre no chat"
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
    papel: Optional[str] = "artista"
    ativo: bool = True
    suspenso_ate: Optional[datetime] = None
    mostrar_moldura_led: bool = True
    mostrar_badge_plano: bool = True
    cor_led_hex: Optional[str] = "#FF793F"
    mensagem_cta: Optional[str] = None
    plano: str = "Free"
    is_verified: bool = False
    termoAceito: Optional[bool] = True
    dataAceiteTermo: Optional[datetime] = None
    versaoTermo: Optional[str] = "v1.0"
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    deletado: bool = False

    @field_validator("cpf", "cpf_cnpj", mode="before")
    @classmethod
    def descriptografar_documento(cls, v: Optional[str]) -> Optional[str]:
        if v:
            from app.core.security import descriptografar_dado
            return descriptografar_dado(v)
        return v

    @field_validator("plano", mode="before")
    @classmethod
    def validar_plano_usuario(cls, v: Optional[str]) -> str:
        return "Free" if not v else str(v)

    @field_validator("tipo_conta", mode="before")
    @classmethod
    def validar_tipo_conta_usuario(cls, v: Optional[str]) -> str:
        return "artista" if not v else str(v)

    @field_validator("tipo_usuario", mode="before")
    @classmethod
    def validar_tipo_usuario_usuario(cls, v: Optional[str]) -> str:
        return "PF" if not v else str(v)

    @field_validator("ativo", "mostrar_moldura_led", "mostrar_badge_plano", mode="before")
    @classmethod
    def validar_booleanos_true_usuario(cls, v: Optional[bool]) -> bool:
        return True if v is None else bool(v)

    @field_validator("deletado", mode="before")
    @classmethod
    def validar_deletado_usuario(cls, v: Optional[bool]) -> bool:
        return False if v is None else bool(v)

    @field_validator("cor_led_hex", mode="before")
    @classmethod
    def validar_cor_led_hex_usuario(cls, v: Optional[str]) -> str:
        return "#FF793F" if not v else str(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TokenResposta(BaseModel):
    """
    Schema de resposta para autenticação bem-sucedida (login / oauth).
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioResposta

    model_config = ConfigDict(from_attributes=True)


class TokenRefreshRequisicao(BaseModel):
    """
    Schema para requisição de renovação de token.
    """
    refresh_token: str = Field(..., description="Refresh token de longa duração")


class TokenRefreshResposta(BaseModel):
    """
    Schema de resposta para token renovado com sucesso.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)


class PerfilPublicoResposta(BaseModel):
    """
    Esquema para perfil público de artistas/usuários visualizado por terceiros.
    """
    id: int
    nome: str
    email: Optional[EmailStr] = None
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
    mostrar_moldura_led: bool = True
    mostrar_badge_plano: bool = True
    cor_led_hex: Optional[str] = "#FF793F"
    mensagem_cta: Optional[str] = None
    plano: str = "Free"
    dataCriacao: Optional[datetime] = Field(None, alias="dataCriacao")
    
    seguidoresCount: int = 0
    seguindoCount: int = 0
    obrasCount: int = 0
    curtidasTotais: int = 0
    visualizacoesTotais: int = 0
    relacionamento: RelacionamentoStatusResposta = Field(default_factory=RelacionamentoStatusResposta)

    @field_validator("plano", mode="before")
    @classmethod
    def validar_plano_perfil(cls, v: Optional[str]) -> str:
        return "Free" if not v else str(v)

    @field_validator("tipo_conta", mode="before")
    @classmethod
    def validar_tipo_conta_perfil(cls, v: Optional[str]) -> str:
        return "artista" if not v else str(v)

    @field_validator("tipo_usuario", mode="before")
    @classmethod
    def validar_tipo_usuario_perfil(cls, v: Optional[str]) -> str:
        return "PF" if not v else str(v)

    @field_validator("mostrar_moldura_led", "mostrar_badge_plano", mode="before")
    @classmethod
    def validar_booleanos_true_perfil(cls, v: Optional[bool]) -> bool:
        return True if v is None else bool(v)

    @field_validator("cor_led_hex", mode="before")
    @classmethod
    def validar_cor_led_perfil(cls, v: Optional[str]) -> str:
        return "#FF793F" if not v else str(v)

    @field_validator("seguidoresCount", "seguindoCount", "obrasCount", "curtidasTotais", "visualizacoesTotais", mode="before")
    @classmethod
    def validar_contagens_perfil(cls, v: Optional[int]) -> int:
        return 0 if v is None else int(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UsuarioItemBusca(BaseModel):
    id: int
    nome: str
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    tipo_conta: str = "artista"
    plano: str = "Free"
    mostrar_moldura_led: bool = True
    mostrar_badge_plano: bool = True
    cor_led_hex: Optional[str] = "#FF793F"

    @field_validator("plano", mode="before")
    @classmethod
    def validar_plano_busca(cls, v: Optional[str]) -> str:
        return "Free" if not v else str(v)

    @field_validator("tipo_conta", mode="before")
    @classmethod
    def validar_tipo_conta_busca(cls, v: Optional[str]) -> str:
        return "artista" if not v else str(v)

    @field_validator("mostrar_moldura_led", "mostrar_badge_plano", mode="before")
    @classmethod
    def validar_booleanos_true_busca(cls, v: Optional[bool]) -> bool:
        return True if v is None else bool(v)

    @field_validator("cor_led_hex", mode="before")
    @classmethod
    def validar_cor_led_busca(cls, v: Optional[str]) -> str:
        return "#FF793F" if not v else str(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class VerificarEmailSchema(BaseModel):
    """
    Esquema para validação do código OTP de 6 dígitos enviado por e-mail via Brevo.
    """
    email: EmailStr
    codigo: str = Field(..., min_length=6, max_length=6, description="Código de verificação OTP de 6 dígitos")


class ReenviarCodigoSchema(BaseModel):
    """
    Esquema para solicitação de reenvio de código OTP para e-mails ainda não verificados.
    """
    email: EmailStr


class RedefinirSenhaSchema(BaseModel):
    """
    Esquema para redefinição/atualização de senha via código OTP.
    """
    email: EmailStr
    codigo: str = Field(..., min_length=6, max_length=6, description="Código OTP de 6 dígitos validado")
    nova_senha: str = Field(..., min_length=6, max_length=100, description="Nova senha de acesso")
    confirmacao_senha: Optional[str] = Field(None, description="Confirmação da nova senha (opcional)")


class RegistroResposta(BaseModel):
    """
    Esquema de resposta retornado após o registo inicial do utilizador.
    """
    mensagem: str
    email: str
    is_verified: bool = False

