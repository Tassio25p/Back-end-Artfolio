from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario_schema import UsuarioCadastro, UsuarioLogin, UsuarioResposta, TokenResposta
from app.services.usuario_service import UsuarioService
from app.repositories.usuario_repository import UsuarioRepository
from app.core.config import settings
from app.models.usuario_model import Usuario

from app.redis_client import redis_client

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Esquema HTTPBearer: exibe apenas o campo de Token no Swagger UI

security = HTTPBearer()

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
    try:
        
        # Decodifica o token JWT usando a chave e o algoritmo configurados

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

    # Busca o usuário ativo no banco de dados
    usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
    if usuario is None:
        raise excecao_credenciais

    return usuario

@router.post("/cadastro", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: UsuarioCadastro, db: Session = Depends(get_db)):
    """
    Cria um novo usuário real no banco de dados.

    Recebe nome, e-mail, CPF, telefone (opcional), senha e tipo de conta.
    Valida e salva no PostgreSQL se não houver conflito de e-mail ou CPF.
    Aplica rate-limiting via Redis (máx. 10 solicitações/min por e-mail).
    """
    # Rate Limiting via Redis
    chave_limit = f"artfolio:ratelimit:cadastro:{dados.email.lower()}"
    tentativas = redis_client.incr(chave_limit, expira_segundos=60)
    if tentativas > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de cadastro. Por favor, aguarde 1 minuto antes de tentar novamente."
        )

    return UsuarioService.cadastrar(db, dados)

@router.post("/login", response_model=TokenResposta)
def logar(dados: UsuarioLogin, db: Session = Depends(get_db)):
    """
    Realiza o login do usuário no sistema.

    Recebe e-mail e senha. Valida as credenciais, e em caso de sucesso,
    retorna um Token JWT e os dados básicos do usuário.
    Aplica rate-limiting via Redis (máx. 10 solicitações/min por e-mail).
    """
    # Rate Limiting via Redis
    chave_limit = f"artfolio:ratelimit:login:{dados.email.lower()}"
    tentativas = redis_client.incr(chave_limit, expira_segundos=60)
    if tentativas > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login consecutivas. Por favor, aguarde 1 minuto antes de tentar novamente."
        )

    return UsuarioService.login(db, dados)

@router.get("/me", response_model=UsuarioResposta)
def obter_me(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    """
    Retorna os dados do usuário atualmente logado.

    Essa rota é protegida e exige um Bearer Token JWT válido no cabeçalho.
    """
    return usuario_atual
