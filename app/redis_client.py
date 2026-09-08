import redis
import logging
from app.core.config import settings

# Configuração do Logger local
logger = logging.getLogger("redis_client")

class SafeRedisClient:
    """
    Cliente Redis com tratamento de erros (Fallback Seguro).

    Tenta se conectar ao Redis. Se o Redis estiver inoperante,
    todos os métodos de cache falham silenciosamente (retornando None/False),
    permitindo que o sistema continue funcionando direto com o PostgreSQL.
    """
    def __init__(self):
        self.client = None
        self.conectar()

    def conectar(self):
        """
        Tenta estabelecer conexão com o Redis usando as configurações atuais.
        """
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2  # Timeout curto para evitar gargalos se estiver offline
            )
            # Testa a conexão
            self.client.ping()
            logger.info("Conectado ao Redis com sucesso!")
        except Exception as e:
            logger.warning(f"Não foi possível conectar ao Redis: {e}. O sistema funcionará sem cache.")
            self.client = None

    def get(self, chave: str) -> str:
        """
        Busca um valor no cache por sua chave.
        Retorna None se a chave não existir ou se o Redis estiver fora do ar.
        """
        if not self.client:
            return None
        try:
            return self.client.get(chave)
        except Exception as e:
            logger.error(f"Erro ao ler do Redis ({chave}): {e}")
            return None

    def set(self, chave: str, valor: str, expira_segundos: int = 3600) -> bool:
        """
        Salva uma chave com valor e tempo de expiração no cache.
        Retorna False se o Redis estiver indisponível.
        """
        if not self.client:
            return False
        try:
            self.client.set(chave, valor, ex=expira_segundos)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar no Redis ({chave}): {e}")
            return False

    def delete(self, chave: str) -> bool:
        """
        Remove uma chave do cache.
        """
        if not self.client:
            return False
        try:
            self.client.delete(chave)
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar chave no Redis ({chave}): {e}")
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """
        Remove todas as chaves que correspondem a um padrão wildcard (ex: 'artfolio:obras:*').
        Retorna False se o Redis estiver indisponível.
        """
        if not self.client:
            return False
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar padrão no Redis ({pattern}): {e}")
            return False

    def incr(self, chave: str, expira_segundos: int = 60) -> int:
        """
        Incrementa o valor de uma chave atômica e ajusta o tempo de expiração na primeira criação.
        Retorna o valor atualizado ou 0 se o Redis estiver indisponível.
        """
        if not self.client:
            return 0
        try:
            valor = self.client.incr(chave)
            if valor == 1:
                self.client.expire(chave, expira_segundos)
            return valor
        except Exception as e:
            logger.error(f"Erro ao incrementar chave no Redis ({chave}): {e}")
            return 0

    def publish(self, canal: str, mensagem: str) -> bool: 
        """
        Publica uma mensagem em um canal do Redis (Pub/Sub) para distribuição em tempo real.
        Retorna True em caso de sucesso ou False se o Redis estiver indisponível.
        """
        if not self.client:
            return False
        try:
            self.client.publish(canal, mensagem)
            return True
        except Exception as e:
            logger.error(f"Erro ao publicar no Redis no canal ({canal}): {e}")
            return False

# Instanciação global para uso em toda a aplicação
redis_client = SafeRedisClient()
