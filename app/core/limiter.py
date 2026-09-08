from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Construção dinâmica da URI de conexão com o Redis
if settings.REDIS_PASSWORD:
    REDIS_URI = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
else:
    REDIS_URI = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# Instância central do Rate Limiter configurada com armazenamento no Redis
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URI,
    default_limits=["120/minute"],
)
