import json
import logging
import asyncio
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import WebSocket
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    """
    Gerenciador central de conexões WebSocket ativas por usuário.
    Permite envio direcionado de mensagens em tempo real e integração com Redis Pub/Sub.
    """

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket, user_id: int):
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        await websocket.accept()
        self.active_connections[user_id].append(websocket)
        logger.info(f"[WebSocket] Usuário {user_id} conectado. Total de conexões ativas: {len(self.active_connections[user_id])}")

    def dispatch_personal_message_sync(self, user_id: int, message: dict):
        if not self.active_connections.get(user_id):
            return
        try:
            running_loop = asyncio.get_running_loop()
            running_loop.create_task(self.send_personal_message(user_id, message))
            return
        except RuntimeError:
            pass
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self.send_personal_message(user_id, message),
                self._loop,
            )

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[WebSocket] Usuário {user_id} desconectado.")

    async def send_personal_message(self, user_id: int, message: dict):
        if user_id not in self.active_connections:
            logger.info(f"[WebSocket] Usuário {user_id} não possui abas ativas conectadas.")
            return

        conexoes = list(self.active_connections[user_id])
        payload = json.dumps(message, ensure_ascii=False)

        for connection in conexoes:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"[WebSocket] Falha ao enviar para usuário {user_id}: {e}. Removendo socket inativo.")
                self.disconnect(connection, user_id)

    async def broadcast(self, message: dict):
        payload = json.dumps(message, ensure_ascii=False)
        for user_id, conexoes in list(self.active_connections.items()):
            for connection in list(conexoes):
                try:
                    await connection.send_text(payload)
                except Exception:
                    self.disconnect(connection, user_id)


manager = ConnectionManager()

# Variável de referência global para impedir o Garbage Collector de apagar a tarefa
subscriber_task: Optional[asyncio.Task] = None


async def iniciar_subscriber_redis():
    """
    Rotina assíncrona executada em background que escuta os canais do Redis Pub/Sub
    no padrão 'notificacoes:*' e repassa imediatamente para os WebSockets correspondentes.
    """
    client: Optional[aioredis.Redis] = None
    pubsub = None

    try:
        while True:
            try:
                client = aioredis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD or None,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                )
                pubsub = client.pubsub()
                await pubsub.psubscribe("notificacoes:*")
                logger.info(f"[Redis Pub/Sub] Inscrito com sucesso no canal 'notificacoes:*' na porta {settings.REDIS_PORT}.")

                async for message in pubsub.listen():
                    if not message:
                        continue

                    msg_type = message.get("type")
                    if msg_type in ("pmessage", "message"):
                        canal = message.get("channel", "")  # ex: "notificacoes:1" ou "notificacoes:usuario:1"
                        data = message.get("data")

                        if canal.startswith("notificacoes:") and data:
                            try:
                                # Pega sempre o último elemento do canal para evitar falhas de formato
                                user_id_str = canal.split(":")[-1]
                                user_id = int(user_id_str)
                                payload = json.loads(data) if isinstance(data, str) else data
                                await manager.send_personal_message(user_id, payload)
                            except Exception as parse_err:
                                logger.error(f"[Redis Pub/Sub] Erro ao despachar mensagem para {canal}: {parse_err}")

            except asyncio.CancelledError:
                logger.info("[Redis Pub/Sub] Tarefa cancelada graciosamente.")
                break
            except Exception as conn_err:
                if pubsub:
                    try:
                        if hasattr(pubsub, "aclose"):
                            await pubsub.aclose()
                        else:
                            await pubsub.close()
                    except Exception:
                        pass
                    pubsub = None
                if client:
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                    client = None
                logger.warning(f"[Redis Pub/Sub] Falha na conexão de mensageria: {conn_err}. Tentando reconectar em 5s...")
                await asyncio.sleep(5)

    finally:
        # Garante o fechamento limpo das conexões com o Redis
        if pubsub:
            try:
                if hasattr(pubsub, "aclose"):
                    await pubsub.aclose()
                else:
                    await pubsub.close()
            except Exception:
                pass
        if client:
            try:
                await client.aclose()
            except Exception:
                pass