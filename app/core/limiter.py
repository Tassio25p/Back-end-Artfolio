import redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Construção dinâmica da URI de conexão com o Redis
if settings.REDIS_PASSWORD:
    REDIS_URI = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
else:
    REDIS_URI = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# Fallback automático: se Redis estiver offline (ex: ambiente de teste/dev local sem docker), usa memória
try:
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        db=settings.REDIS_DB,
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
    )
    r.ping()
    storage_escolhido = REDIS_URI
except Exception:
    storage_escolhido = "memory://"

# Instância central do Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_escolhido,
    default_limits=["120/minute"],
)
