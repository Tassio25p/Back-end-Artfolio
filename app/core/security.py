import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import settings

def criptografar_senha(senha: str) -> str:
    """
    Cria um hash seguro para a senha informada.

    Essa função recebe a senha plana (texto puro),
    converte para bytes, aplica o algoritmo bcrypt nativo com gensalt
    e retorna o hash gerado como string decodificada.
    """
    senha_bytes = senha.encode("utf-8")
    # Gera um salt aleatório e aplica o hash
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha_bytes, salt)
    return hash_bytes.decode("utf-8")

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """
    Compara uma senha em texto puro com o hash salvo no banco.

    Garante que a comparação seja feita de forma segura contra ataques de timing.
    """
    try:
        senha_plana_bytes = senha_plana.encode("utf-8")
        senha_hash_bytes = senha_hash.encode("utf-8")
        return bcrypt.checkpw(senha_plana_bytes, senha_hash_bytes)
    except Exception:
        # Retorna False se houver algum erro de tipo de dados (ex: hash corrompido)
        return False

def criar_token_acesso(dados: dict, expira_em: Union[timedelta, None] = None) -> str:
    """
    Gera um token JWT assinado para autenticação.

    Essa função codifica os dados fornecidos no payload (reivindicações)
    do token, adiciona uma data de expiração e assina com a chave secreta.
    """
    para_codificar = dados.copy()
    
    if expira_em:
        data_expiracao = datetime.now(timezone.utc) + expira_em
    else:
        data_expiracao = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    para_codificar.update({"exp": data_expiracao})
    
    token_jwt = jwt.encode(
        para_codificar, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token_jwt
