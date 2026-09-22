from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.usuario_schema import (
    UsuarioCadastro,
    UsuarioLogin,
    UsuarioResposta,
    TokenResposta,
    GoogleLoginSchema,
    TokenRefreshRequisicao,
    TokenRefreshResposta,
    VerificarEmailSchema,
    ReenviarCodigoSchema,
    RedefinirSenhaSchema,
    RegistroResposta,
)
from app.services.usuario_service import UsuarioService
from app.repositories.usuario_repository import UsuarioRepository
from app.core.config import settings
from app.models.usuario_model import Usuario
from app.redis_client import redis_client
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Esquema HTTPBearer: exibe apenas o campo de Token no Swagger UI
security = HTTPBearer()
security_opcional = HTTPBearer(auto_error=False)


def obter_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Injeta o usuário atualmente autenticado nas rotas privadas.

    Extrai o token JWT do cabeçalho Authorization: Bearer <token>,
    decodifica-o, valida a expiração e busca o usuário no banco de dados.
    """
    token = credentials.credentials
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        # Correção linha 49: payload.get pode ser None, aceitamos Optional[str]
        usuario_id_raw: Optional[str] = payload.get("sub")    
        if not usuario_id_raw:
            raise excecao_credenciais
        usuario_id = int(usuario_id_raw)
    except (JWTError, ValueError):
        raise excecao_credenciais

    usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
    if usuario is None:
        raise excecao_credenciais

    return usuario


# Alias padronizado para get_current_user
get_current_user = obter_usuario_atual


def obter_usuario_opcional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_opcional),
    db: Session = Depends(get_db)
) -> Optional[Usuario]:
    """
    Injeta o usuário autenticado caso o token exista e seja válido,
    ou retorna None para requisições de visitantes.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        # Correção linha 83: tipagem segura para valor opcional
        usuario_id_raw: Optional[str] = payload.get("sub")
        if usuario_id_raw:
            return UsuarioRepository.buscar_por_id(db, int(usuario_id_raw))
    except Exception:
        return None
    return None


@router.post(
    "/registar",
    response_model=RegistroResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Registar novo utilizador e enviar código OTP de verificação via Brevo"
)
def registar(dados: UsuarioCadastro, db: Session = Depends(get_db)):
    """
    Recebe os dados de registo, verifica se o e-mail já existe, gera um código OTP de 6 dígitos,
    guarda o utilizador com is_verified = False, dispara o envio do e-mail via Brevo e retorna mensagem de sucesso.
    """
    chave_limit = f"artfolio:ratelimit:cadastro:{dados.email.lower()}"
    tentativas = redis_client.incr(chave_limit, expira_segundos=60)
    if tentativas > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de registo. Por favor, aguarde 1 minuto antes de tentar novamente."
        )

    usuario_criado = UsuarioService.cadastrar(db, dados)
    return {
        "mensagem": "Utilizador registado com sucesso! Enviamos um código de verificação de 6 dígitos para o seu e-mail.",
        "email": usuario_criado.email or dados.email,
        "is_verified": False
    }


@router.post(
    "/verificar-email",
    status_code=status.HTTP_200_OK,
    summary="Verificar e-mail com código OTP de 6 dígitos"
)
@limiter.limit("10/minute")
def verificar_email(request: Request, dados: VerificarEmailSchema, db: Session = Depends(get_db)):
    """
    Recebe o e-mail e o código OTP, valida se corresponde ao gravado no banco de dados,
    atualiza is_verified = True e limpa o código temporário.
    """
    return UsuarioService.verificar_email(db, dados.email, dados.codigo)


@router.post(
    "/reenviar-codigo",
    status_code=status.HTTP_200_OK,
    summary="Reenviar código de verificação OTP por e-mail"
)
@limiter.limit("5/minute")
def reenviar_codigo(request: Request, dados: ReenviarCodigoSchema, db: Session = Depends(get_db)):
    """
    Gera um novo código OTP de 6 dígitos e reenvia para o e-mail do utilizador via Brevo.
    """
    return UsuarioService.reenviar_codigo(db, dados.email)


@router.post(
    "/esqueci-senha",
    status_code=status.HTTP_200_OK,
    summary="Solicitar código OTP para recuperação de senha"
)
@limiter.limit("5/minute")
def esqueci_senha(request: Request, dados: ReenviarCodigoSchema, db: Session = Depends(get_db)):
    """
    Gera um novo código OTP de 6 dígitos para recuperação de senha e envia para o e-mail via Brevo.
    """
    return UsuarioService.solicitar_recuperacao_senha(db, dados.email)


@router.post(
    "/atualizar-senha",
    status_code=status.HTTP_200_OK,
    summary="Atualizar/redefinir senha com código OTP validado"
)
@router.post(
    "/redefinir-senha",
    status_code=status.HTTP_200_OK,
    summary="Alias para redefinir senha com código OTP"
)
@limiter.limit("5/minute")
def atualizar_senha(request: Request, dados: RedefinirSenhaSchema, db: Session = Depends(get_db)):
    """
    Recebe e-mail, código OTP e nova senha, valida a chave e atualiza as credenciais do utilizador.
    """
    return UsuarioService.redefinir_senha(db, dados.email, dados.codigo, dados.nova_senha)


@router.post("/cadastro", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: UsuarioCadastro, db: Session = Depends(get_db)):
    """
    Cria um novo usuário real no banco de dados (rota compatível com versões existentes do frontend).
    """
    chave_limit = f"artfolio:ratelimit:cadastro:{dados.email.lower()}"
    tentativas = redis_client.incr(chave_limit, expira_segundos=60)
    if tentativas > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de cadastro. Por favor, aguarde 1 minuto antes de tentar novamente."
        )

    return UsuarioService.cadastrar(db, dados)


@router.post("/login", response_model=TokenResposta)
@limiter.limit("5/minute")
def logar(request: Request, dados: UsuarioLogin, db: Session = Depends(get_db)):
    """
    Realiza o login do usuário no sistema.
    """
    chave_limit = f"artfolio:ratelimit:login:{dados.email.lower()}"
    tentativas = redis_client.incr(chave_limit, expira_segundos=60)
    if tentativas > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login consecutivas. Por favor, aguarde 1 minuto antes de tentar novamente."
        )

    return UsuarioService.login(db, dados)


@router.post("/google", response_model=TokenResposta, summary="Login ou Cadastro com Google")
@limiter.limit("5/minute")
def login_google(request: Request, dados: GoogleLoginSchema, db: Session = Depends(get_db)):
    """
    Autentica ou cadastra um usuário automaticamente utilizando o ID token do Google.
    """
    return UsuarioService.login_google(db, dados.token)


@router.post("/refresh", response_model=TokenRefreshResposta, summary="Renovação de Sessão (Refresh Token)")
@limiter.limit("20/minute")
def renovar_token(request: Request, dados: TokenRefreshRequisicao, db: Session = Depends(get_db)):
    """
    Renova o token de acesso de curta duração utilizando o Refresh Token assinado (7 dias).
    """
    return UsuarioService.renovar_token(db, dados.refresh_token)


@router.get("/me", response_model=UsuarioResposta)
def obter_me(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna os dados do usuário atualmente logado enriquecidos com o plano ativo.
    """
    from app.services.plano_service import PlanoService
    usuario_atual.plano = PlanoService.obter_tipo_plano_usuario(db, usuario_atual.id)
    return usuario_atual