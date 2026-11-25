import bcrypt
import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from jose import jwt, JWTError
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

def _obter_fernet() -> Fernet:
    """
    Deriva uma chave de 32 bytes compatível com URL-safe base64 do Fernet a partir da chave configurada.
    """
    chave_secreta = (settings.DATA_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")
    hash_32 = hashlib.sha256(chave_secreta).digest()
    chave_base64 = base64.urlsafe_b64encode(hash_32)
    return Fernet(chave_base64)

def criptografar_senha(senha: str) -> str:
    """
    Cria um hash seguro para a senha informada usando bcrypt nativo.
    """
    senha_bytes = senha.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hash_bytes = bcrypt.hashpw(senha_bytes, salt)
    return hash_bytes.decode("utf-8")

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """
    Compara uma senha em texto puro com o hash salvo no banco de dados.
    """
    try:
        senha_plana_bytes = senha_plana.encode("utf-8")
        senha_hash_bytes = senha_hash.encode("utf-8")
        return bcrypt.checkpw(senha_plana_bytes, senha_hash_bytes)
    except Exception:
        return False

def criar_token_acesso(dados: dict, expira_em: Union[timedelta, None] = None) -> str:
    """
    Gera um token JWT assinado de curta duração (30 minutos por padrão).
    """
    para_codificar = dados.copy()
    if expira_em:
        data_expiracao = datetime.now(timezone.utc) + expira_em
    else:
        data_expiracao = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    para_codificar.update({
        "exp": data_expiracao,
        "type": "access"
    })
    
    return jwt.encode(
        para_codificar, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )

def criar_token_refresh(dados: dict, expira_em: Union[timedelta, None] = None) -> str:
    """
    Gera um refresh token JWT assinado de longa duração (7 dias por padrão).
    """
    para_codificar = dados.copy()
    if expira_em:
        data_expiracao = datetime.now(timezone.utc) + expira_em
    else:
        data_expiracao = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    para_codificar.update({
        "exp": data_expiracao,
        "type": "refresh"
    })
    
    return jwt.encode(
        para_codificar, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )

def validar_token_jwt(token: str, tipo_esperado: Optional[str] = "access") -> dict:
    """
    Decodifica e valida o token JWT.
    Lança ValueError caso seja inválido, expirado ou do tipo incorreto.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        tipo = payload.get("type", "access")
        if tipo_esperado and tipo != tipo_esperado:
            raise ValueError(f"Tipo de token inválido. Esperado '{tipo_esperado}', recebido '{tipo}'.")
        return payload
    except JWTError as e:
        raise ValueError(f"Token inválido ou expirado: {str(e)}")

def gerar_hash_busca_cpf(documento: str) -> str:
    """
    Gera um hash determinístico cego (HMAC-SHA256) dos dígitos do documento.
    Permite busca exata e verificação de unicidade no banco sem expor o CPF/CNPJ em texto puro.
    """
    if not documento:
        return ""
    digitos = "".join(filter(str.isdigit, str(documento)))
    chave = (settings.DATA_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")
    h = hmac.new(chave, digitos.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()

def criptografar_dado(texto: Optional[str]) -> Optional[str]:
    """
    Criptografa um dado sensível em repouso usando AES (Fernet).
    """
    if not texto:
        return None
    fernet = _obter_fernet()
    cifrado = fernet.encrypt(texto.encode("utf-8"))
    return cifrado.decode("utf-8")

def descriptografar_dado(texto_cifrado: Optional[str]) -> Optional[str]:
    """
    Descriptografa um dado protegido em repouso.
    Se o dado não estiver criptografado (ex: legado em plaintext), retorna o próprio texto com segurança.
    """
    if not texto_cifrado:
        return None
    try:
        fernet = _obter_fernet()
        decriptado = fernet.decrypt(texto_cifrado.encode("utf-8"))
        return decriptado.decode("utf-8")
    except (InvalidToken, Exception):
        # Fallback de compatibilidade caso o registro ainda esteja em plaintext
        return texto_cifrado

