from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario_schema import UsuarioCadastro, UsuarioLogin, UsuarioResposta, TokenResposta, GoogleLoginSchema
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
# endpoint de obtenção de usuario atual
def obter_usuario_atual(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> Usuario:
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
    try: # esse try execpt faz a validação do token, verificando se ele é válido e se o usuário existe no banco de dados
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        usuario_id_str: str = payload.get("sub")
        if usuario_id_str is None:
            raise excecao_credenciais
        usuario_id = int(usuario_id_str)
    except (JWTError, ValueError):
        raise excecao_credenciais

    usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
    if usuario is None:
        raise excecao_credenciais

    return usuario

# Alias padronizado para get_current_user
get_current_user = obter_usuario_atual

 # endpoint de obtenção de usuario opcional
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
    try: # esse try execpt faz a validação do token verificando se ele é válido e se o usuário existe no banco de dados
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        usuario_id_str: str = payload.get("sub")
        if usuario_id_str:
            return UsuarioRepository.buscar_por_id(db, int(usuario_id_str))
    except Exception:
        return None
    return None
 # esse endpoint e pra cadastrar usuario
@router.post("/cadastro", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: UsuarioCadastro, db: Session = Depends(get_db)):
    """
    Cria um novo usuário real no banco de dados.
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
