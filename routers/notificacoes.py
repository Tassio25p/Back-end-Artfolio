"""
Re-exportação do router de notificações de app/routers/notificacoes.py
para compatibilidade total com importações 'routers.notificacoes'.
"""
from app.routers.notificacoes import (
    router,
    websocket_notificacoes,
    listar_notificacoes,
    marcar_todas_como_lidas,
    marcar_como_lida,
    deletar_todas,
    deletar_notificacao,
    listar_todas,
    contar_nao_lidas,
)

notificacoes_router = router

__all__ = [
    "router",
    "notificacoes_router",
    "websocket_notificacoes",
    "listar_notificacoes",
    "marcar_todas_como_lidas",
    "marcar_como_lida",
    "deletar_todas",
    "deletar_notificacao",
    "listar_todas",
    "contar_nao_lidas",
]
