import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict
from typing import Optional
from datetime import datetime

class UsuarioBase(BaseModel):
    """
    Schema base contendo os campos comuns a todas as operações de usuário.
    """
    nome: str = Field(..., min_length=2, max_length=100, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="E-mail único de acesso")
    cpf: str = Field(..., description="CPF apenas com números (11 ou 14 dígitos)")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone de contato")
    biografia: Optional[str] = Field(None, description="Biografia ou apresentação do usuário")
    portfolio: Optional[str] = Field(None, max_length=255, description="Link do portfólio do usuário")
    tipo_conta: str = Field("cliente", description="Papel do usuário no sistema: cliente, artista, moderador ou admin")

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        """
        Valida o tamanho do CPF (11 para CPF físico ou 14 para CNPJ/registro similar).
        Remove caracteres não numéricos antes da validação.
        """
        # Mantém apenas os dígitos numéricos
        somente_numeros = "".join(filter(str.isdigit, v))
        if len(somente_numeros) not in (11, 14):
            raise ValueError("O CPF deve conter exatamente 11 dígitos (ou 14 para CNPJ/similar).")
        return somente_numeros

    @field_validator("tipo_conta")
    @classmethod
    def validar_tipo_conta(cls, v: str) -> str:
        """
        Valida se o tipo de conta fornecido é um dos papéis válidos no sistema.
        """
        tipos_validos = ["cliente", "artista", "moderador", "admin"]
        v_lowered = v.lower()
        if v_lowered not in tipos_validos:
            raise ValueError(f"Tipo de conta inválido. Deve ser um dos seguintes: {', '.join(tipos_validos)}.")
        return v_lowered

class UsuarioCadastro(UsuarioBase):
    """
    Esquema para requisição de cadastro de um novo usuário.
    Exige a senha em texto puro.
    """
    senha: str = Field(..., min_length=6, max_length=100, description="Senha de acesso (mínimo de 6 caracteres)")

class UsuarioLogin(BaseModel):
    """
    Esquema para requisição de login.
    """
    email: EmailStr = Field(..., description="E-mail cadastrado")
    senha: str = Field(..., description="Senha de acesso")

class UsuarioUpdateSchema(BaseModel):
    """
    Schema para atualização parcial do perfil do usuário autenticado.

    Todos os campos são opcionais — somente os informados na requisição
    serão atualizados. Campos ausentes permanecem inalterados.

    Exemplo de uso:
        PUT /usuarios/me
        {
            "nome": "João Silva",
            "instagram": "joaosilva"
        }
    """
    nome: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Nome completo do usuário (mínimo 3, máximo 100 caracteres)",
        json_schema_extra={"example": "João Silva"}
    )
    telefone: Optional[str] = Field(
        None,
        max_length=20,
        description="Telefone de contato com DDD",
        json_schema_extra={"example": "(11) 99999-9999"}
    )
    biografia: Optional[str] = Field(
        None,
        max_length=1000,
        description="Biografia ou apresentação do usuário (máximo 1000 caracteres)",
        json_schema_extra={"example": "Artista digital apaixonado por ilustração e design."}
    )
    fotoPerfil: Optional[str] = Field(
        None,
        max_length=255,
        description="URL da foto de perfil do usuário",
        json_schema_extra={"example": "https://exemplo.com/fotos/perfil.jpg"}
    )
    portfolio: Optional[str] = Field(
        None,
        max_length=255,
        description="Link do portfólio do usuário",
        json_schema_extra={"example": "https://meuportfolio.com"}
    )
    instagram: Optional[str] = Field(
        None,
        max_length=255,
        description="Usuário do Instagram (aceita 'usuario' ou 'https://instagram.com/usuario')",
        json_schema_extra={"example": "joaosilva"}
    )
    behance: Optional[str] = Field(
        None,
        max_length=255,
        description="Usuário do Behance (aceita 'usuario' ou 'https://behance.net/usuario')",
        json_schema_extra={"example": "joaosilva"}
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="URL do site pessoal do usuário (deve começar com http:// ou https://)",
        json_schema_extra={"example": "https://meusite.com.br"}
    )

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida o formato do telefone.
        Aceita formatos como (11) 99999-9999 ou apenas dígitos (10-11 dígitos).
        """
        if v is None:
            return v
        somente_numeros = "".join(filter(str.isdigit, v))
        if len(somente_numeros) < 10 or len(somente_numeros) > 11:
            raise ValueError("O telefone deve conter entre 10 e 11 dígitos numéricos.")
        return v

    @field_validator("instagram")
    @classmethod
    def validar_instagram(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida e normaliza o campo Instagram.
        Aceita o handle direto ('usuario') ou a URL completa ('https://instagram.com/usuario').
        Sempre salva apenas o handle.
        """
        if v is None:
            return v
        v = v.strip()
        # Remove URL prefix se presente
        padrao_url = re.compile(
            r"^(?:https?://)?(?:www\.)?instagram\.com/(.+?)/?$", re.IGNORECASE
        )
        match = padrao_url.match(v)
        if match:
            return match.group(1)
        # Se não é URL, deve ser um handle válido (sem espaços, sem barras)
        if "/" in v or " " in v:
            raise ValueError(
                "Instagram inválido. Informe o usuário (ex: 'joaosilva') "
                "ou a URL (ex: 'https://instagram.com/joaosilva')."
            )
        return v

    @field_validator("behance")
    @classmethod
    def validar_behance(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida e normaliza o campo Behance.
        Aceita o handle direto ('usuario') ou a URL completa ('https://behance.net/usuario').
        Sempre salva apenas o handle.
        """
        if v is None:
            return v
        v = v.strip()
        # Remove URL prefix se presente
        padrao_url = re.compile(
            r"^(?:https?://)?(?:www\.)?behance\.net/(.+?)/?$", re.IGNORECASE
        )
        match = padrao_url.match(v)
        if match:
            return match.group(1)
        # Se não é URL, deve ser um handle válido (sem espaços, sem barras)
        if "/" in v or " " in v:
            raise ValueError(
                "Behance inválido. Informe o usuário (ex: 'joaosilva') "
                "ou a URL (ex: 'https://behance.net/joaosilva')."
            )
        return v

    @field_validator("website")
    @classmethod
    def validar_website(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida se o website é uma URL válida com protocolo HTTP/HTTPS.
        """
        if v is None:
            return v
        v = v.strip()
        padrao_url = re.compile(
            r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE
        )
        if not padrao_url.match(v):
            raise ValueError(
                "URL do website inválida. Deve começar com http:// ou https:// "
                "(ex: 'https://meusite.com.br')."
            )
        return v


class UsuarioSenhaSchema(BaseModel):
    """
    Schema para alteração de senha do usuário autenticado.

    Exige a senha atual para confirmação de identidade, a nova senha
    e a confirmação da nova senha.

    Exemplo de uso:
        PATCH /usuarios/me/senha
        {
            "senhaAtual": "minhasenha123",
            "novaSenha": "novasenha456",
            "confirmacaoSenha": "novasenha456"
        }
    """
    senhaAtual: str = Field(
        ...,
        description="Senha atual do usuário para confirmação de identidade",
        json_schema_extra={"example": "minhasenha123"}
    )
    novaSenha: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Nova senha desejada (mínimo 6 caracteres)",
        json_schema_extra={"example": "novasenha456"}
    )
    confirmacaoSenha: str = Field(
        ...,
        description="Confirmação da nova senha (deve ser idêntica à novaSenha)",
        json_schema_extra={"example": "novasenha456"}
    )

    @model_validator(mode="after")
    def validar_confirmacao_senha(self) -> "UsuarioSenhaSchema":
        """
        Valida se a nova senha e a confirmação são idênticas.
        """
        if self.novaSenha != self.confirmacaoSenha:
            raise ValueError("A nova senha e a confirmação não coincidem.")
        return self


class UsuarioResposta(BaseModel):
    """
    Esquema para expor os dados do usuário nas respostas da API.
    Não retorna a senha hashada sob nenhuma circunstância.
    """
    id: int
    nome: str
    email: EmailStr
    cpf: str
    telefone: Optional[str]
    biografia: Optional[str]
    fotoPerfil: Optional[str] = Field(None, alias="fotoPerfil")
    portfolio: Optional[str]
    instagram: Optional[str]
    behance: Optional[str]
    website: Optional[str]
    tipo_conta: str
    dataCriacao: datetime = Field(None, alias="dataCriacao")
    deletado: bool

    # Configuração do Pydantic v2 para serializar a partir dos atributos de objetos SQLAlchemy (antigo orm_mode=True)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class TokenResposta(BaseModel):
    """
    Esquema retornado ao efetuar login com sucesso.
    """
    token_acesso: str = Field(..., alias="access_token")
    tipo_token: str = Field("bearer", alias="token_type")
    usuario: UsuarioResposta

    model_config = ConfigDict(populate_by_name=True)
