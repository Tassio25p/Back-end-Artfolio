# Bibliotecas
import os
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import validar_token_jwt
from app.core.websocket_manager import manager, iniciar_subscriber_redis
from app.database import engine, Base, SessionLocal
from app.services.trending_service import TrendingService

# Controllers
from app.controllers import (
    auth_controller,
    postagem_controller,
    artista_controller,
    usuario_controller,
    feed_controller,
    notificacao_controller,
    admin_controller,
    mensagem_controller,
    plano_controller,
    trending_controller,
    pagamento_controller,
)


# Modelos
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.postagem_categoria_model import PostagemCategoria
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.seguidor_model import Seguidor
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.models.denuncia_model import Denuncia
from app.models.usuario_model import Usuario
from app.models.log_auditoria_model import LogAuditoria

# Criação dos diretórios de upload
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "perfis"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "certificados"), exist_ok=True)

# Criação das tabelas e auto-migração do esquema no PostgreSQL
try:
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.connect() as conn:
        tabela_usuario_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'usuario')"
        )).scalar()

        if tabela_usuario_existe:
            colunas_usuario = {
                "tipo_usuario": "VARCHAR(20) DEFAULT 'PF'",
                "tipo_conta": "VARCHAR(20) DEFAULT 'artista'",
                "instagram": "VARCHAR(255)",
                "behance": "VARCHAR(255)",
                "website": "VARCHAR(255)",
                "termoaceito": "BOOLEAN DEFAULT FALSE",
                "dataaceitetermo": "TIMESTAMP",
                "versaotermo": "VARCHAR(10)",
                "trajetoria": "TEXT",
                "especializacoes": "TEXT",
                "certificados": "TEXT",
                "mostrar_moldura_led": "BOOLEAN DEFAULT TRUE",
                "mostrar_badge_plano": "BOOLEAN DEFAULT TRUE",
                "cor_led_hex": "VARCHAR(20) DEFAULT '#FF793F'",
                "mensagem_cta": "TEXT",
                "cpf_hash": "VARCHAR(64)",
                "ativo": "BOOLEAN DEFAULT TRUE",
                "suspenso_ate": "TIMESTAMP",
                "codigo_verificacao": "VARCHAR(10)",
                "is_verified": "BOOLEAN DEFAULT FALSE",
            }
            # Garantir expansão do campo cpf_cnpj para armazenar criptografia AES
            try:
                conn.execute(text("ALTER TABLE usuario ALTER COLUMN cpf_cnpj TYPE VARCHAR(500)"))
                conn.commit()
            except Exception:
                pass

            for coluna, tipo in colunas_usuario.items():
                coluna_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = 'usuario' AND column_name = '{coluna}')"
                )).scalar()
                if not coluna_existe:
                    conn.execute(text(
                        f"ALTER TABLE usuario ADD COLUMN {coluna} {tipo}"
                    ))
                    conn.commit()
                    print(f"[OK] Coluna '{coluna}' adicionada com sucesso à tabela 'usuario'.")

        tabela_postagem_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'postagem')"
        )).scalar()

        if tabela_postagem_existe:
            coluna_vis_existe = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'postagem' AND column_name = 'visualizacoes')"
            )).scalar()
            if not coluna_vis_existe:
                conn.execute(text(
                    "ALTER TABLE postagem ADD COLUMN visualizacoes BIGINT DEFAULT 0"
                ))
                conn.commit()
                print("[OK] Coluna 'visualizacoes' adicionada com sucesso à tabela 'postagem'.")

            coluna_status_existe = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'postagem' AND column_name = 'status')"
            )).scalar()
            if not coluna_status_existe:
                conn.execute(text(
                    "ALTER TABLE postagem ADD COLUMN status VARCHAR(30) DEFAULT 'publicada'"
                ))
                conn.commit()
                print("[OK] Coluna 'status' adicionada com sucesso à tabela 'postagem'.")

            # Garantir tabela postagem_categoria
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS postagem_categoria (
                    id SERIAL PRIMARY KEY,
                    idpostagem INTEGER NOT NULL REFERENCES postagem(id) ON DELETE CASCADE,
                    idcategoria INTEGER NOT NULL REFERENCES categoria(id) ON DELETE CASCADE,
                    datacriacao TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.commit()

            # Garantir tabela postagem_visualizacao (anti-farm de views)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS postagem_visualizacao (
                    id SERIAL PRIMARY KEY,
                    idpostagem INTEGER NOT NULL REFERENCES postagem(id) ON DELETE CASCADE,
                    idusuario INTEGER REFERENCES usuario(id) ON DELETE CASCADE,
                    datacriacao TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.commit()

        # Garantir tabela logs_auditoria
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id SERIAL PRIMARY KEY,
                moderador_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                acao VARCHAR(100) NOT NULL,
                alvo_tipo VARCHAR(50) NOT NULL,
                alvo_id INTEGER NOT NULL,
                detalhes TEXT,
                criado_em TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.commit()

        # Garantir colunas de moderação em denuncia_chat
        tabela_denuncia_chat_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'denuncia_chat')"
        )).scalar()
        if tabela_denuncia_chat_existe:
            colunas_dc = {
                "nota_moderador": "TEXT",
                "moderador_id": "INTEGER REFERENCES usuario(id)",
                "resolvido_em": "TIMESTAMP"
            }
            for coluna, tipo in colunas_dc.items():
                coluna_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = 'denuncia_chat' AND column_name = '{coluna}')"
                )).scalar()
                if not coluna_existe:
                    conn.execute(text(f"ALTER TABLE denuncia_chat ADD COLUMN {coluna} {tipo}"))
                    conn.commit()
                    print(f"[OK] Coluna '{coluna}' adicionada com sucesso à tabela 'denuncia_chat'.")

        # Garantir colunas em mensagem
        tabela_msg_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mensagem')"
        )).scalar()
        if tabela_msg_existe:
            colunas_msg = {
                "deletado_por": "VARCHAR(255) DEFAULT ''",
                "lida": "BOOLEAN DEFAULT FALSE",
                "editado_em": "TIMESTAMP",
                "deletado_em": "TIMESTAMP",
                "deletado_por_id": "INTEGER REFERENCES usuario(id)",
                "datadelecao": "TIMESTAMP",
                "deletado": "BOOLEAN DEFAULT FALSE",
                "dataenvio": "TIMESTAMP DEFAULT NOW()",
                "arquivourl": "VARCHAR(255)",
            }
            for coluna, tipo in colunas_msg.items():
                col_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'mensagem' AND column_name = '{coluna}')"
                )).scalar()
                if not col_existe:
                    conn.execute(text(f"ALTER TABLE mensagem ADD COLUMN {coluna} {tipo}"))
                    conn.commit()
                    print(f"[OK] Coluna '{coluna}' adicionada com sucesso à tabela 'mensagem'.")

        # Garantir colunas em conversa e conversausuario
        tabela_conversa_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversa')"
        )).scalar()
        if tabela_conversa_existe:
            colunas_conversa = {
                "datacriacao": "TIMESTAMP DEFAULT NOW()",
                "deletado": "BOOLEAN DEFAULT FALSE",
                "datadelecao": "TIMESTAMP"
            }
            for coluna, tipo in colunas_conversa.items():
                col_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversa' AND column_name = '{coluna}')"
                )).scalar()
                if not col_existe:
                    conn.execute(text(f"ALTER TABLE conversa ADD COLUMN {coluna} {tipo}"))
                    conn.commit()
                    print(f"[OK] Coluna '{coluna}' adicionada com sucesso à tabela 'conversa'.")

        tabela_cu_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversausuario')"
        )).scalar()
        if tabela_cu_existe:
            colunas_cu = {
                "dataentrada": "TIMESTAMP DEFAULT NOW()",
                "deletado": "BOOLEAN DEFAULT FALSE",
                "datadelecao": "TIMESTAMP"
            }
            for coluna, tipo in colunas_cu.items():
                col_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversausuario' AND column_name = '{coluna}')"
                )).scalar()
                if not col_existe:
                    conn.execute(text(f"ALTER TABLE conversausuario ADD COLUMN {coluna} {tipo}"))
                    conn.commit()
                    print(f"[OK] Coluna '{coluna}' adicionada com sucesso à tabela 'conversausuario'.")

        # Garantir colunas da Central de Notificações
        tabela_notif_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notificacao')"
        )).scalar()
        if tabela_notif_existe:
            for col, col_tipo in [("referencia_id", "INTEGER"), ("link_acao", "VARCHAR(255)")]:
                col_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'notificacao' AND column_name = '{col}')"
                )).scalar()
                if not col_existe:
                    conn.execute(text(f"ALTER TABLE notificacao ADD COLUMN {col} {col_tipo}"))
                    conn.commit()
                    print(f"[OK] Coluna '{col}' adicionada com sucesso à tabela 'notificacao'.")


        # Garantir sementes dos planos padrão (Free, Pro, Boost)
        tabela_plano_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'plano')"
        )).scalar()
        if tabela_plano_existe:
            qtd_planos = conn.execute(text("SELECT COUNT(*) FROM plano WHERE deletado = FALSE")).scalar()
            if qtd_planos == 0:
                conn.execute(text("""
                    INSERT INTO plano (tipo, precoplano, descricao, isativo, deletado)
                    VALUES 
                        ('Free', 0.00, 'Plano essencial para todos os usuários do Artfolio', TRUE, FALSE),
                        ('Pro', 29.90, 'Plano profissional com carrosséis, estatísticas e suporte avançado', TRUE, FALSE),
                        ('Boost', 49.90, 'Plano de alcance máximo com destaque no feed e prioridade orgânica', TRUE, FALSE);
                """))
                conn.commit()
                print("[OK] Planos padrão (Free, Pro, Boost) semeados com sucesso na tabela 'plano'.")

except Exception as e:
    import traceback
    print("[ERRO] ERRO AO SINCRONIZAR O BANCO:")
    traceback.print_exc()


# Rotinas Assíncronas de Background
async def rotina_atualizacao_trending():
    """
    Rotina assíncrona em background que recalcula o trending (Time Decay) a cada 30 minutos (1800s).
    """
    try:
        while True:
            try:
                db = SessionLocal()
                try:
                    TrendingService.calcular_e_salvar_trending(db)
                finally:
                    db.close()
            except Exception as e:
                print(f"[Trending Background] Erro ao atualizar cache: {e}")
            await asyncio.sleep(1800)
    except asyncio.CancelledError:
        print("[Trending Background] Rotina encerrada com sucesso.")


# Conjunto global para guardar referências fortes das tarefas e evitar o Garbage Collector
tarefas_background = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: inicializa as rotinas e armazena as tarefas
    task_trending = asyncio.create_task(rotina_atualizacao_trending())
    task_redis = asyncio.create_task(iniciar_subscriber_redis())
    
    tarefas_background.add(task_trending)
    tarefas_background.add(task_redis)
    
    task_trending.add_done_callback(tarefas_background.discard)
    task_redis.add_done_callback(tarefas_background.discard)
    
    yield  # A aplicação roda aqui
    
    # 2. Shutdown / Hot-reload: cancela as tarefas graciosamente sem estourar alertas
    for task in list(tarefas_background):
        task.cancel()
    
    await asyncio.gather(*tarefas_background, return_exceptions=True)
    tarefas_background.clear()


# Criação da API com lifespan gerenciado
app = FastAPI(
    title="Artfolio API",
    description="Backend para a plataforma artística digital Artfolio.",
    version="1.0.0",
    lifespan=lifespan
)

# Origens permitidas para requisições cross-origin (CORS)
ORIGENS_PERMITIDAS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Configuração estrita e completa do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware de Security Headers (OWASP Hardening)
@app.middleware("http")
async def adicionar_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as exc:
        origem = request.headers.get("origin")
        origem_permitida = origem if origem in ORIGENS_PERMITIDAS else ORIGENS_PERMITIDAS[0]
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor.", "erro": str(exc)},
            headers={
                "Access-Control-Allow-Origin": origem_permitida,
                "Access-Control-Allow-Credentials": "true",
            }
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Configuração do Rate Limiting (SlowAPI + Redis)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "status": 429,
            "erro": "RateLimitExceeded",
            "mensagem": "Você fez muitas requisições em pouco tempo. Aguarde um minuto e tente novamente.",
            "detalhes": exc.detail,
        },
    )

from fastapi.exceptions import ResponseValidationError

@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    import logging
    logging.error(f"ResponseValidationError em {request.url}: {exc.errors()}")
    origem = request.headers.get("origin")
    origem_permitida = origem if origem in ORIGENS_PERMITIDAS else ORIGENS_PERMITIDAS[0]
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro de validação de resposta da API.", "erros": str(exc.errors())},
        headers={
            "Access-Control-Allow-Origin": origem_permitida,
            "Access-Control-Allow-Credentials": "true",
        }
    )

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException as FastAPIHTTPException

@app.exception_handler(FastAPIHTTPException)
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    origem = request.headers.get("origin")
    origem_permitida = origem if origem in ORIGENS_PERMITIDAS else ORIGENS_PERMITIDAS[0]
    headers = getattr(exc, "headers", None) or {}
    headers["Access-Control-Allow-Origin"] = origem_permitida
    headers["Access-Control-Allow-Credentials"] = "true"

    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=headers)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)

# Inclusão dos roteadores de controllers da aplicação
app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(postagem_controller.router)
app.include_router(artista_controller.router)
app.include_router(feed_controller.router)
app.include_router(notificacao_controller.router)
app.include_router(admin_controller.router)
app.include_router(mensagem_controller.router)
app.include_router(mensagem_controller.chat_router)
app.include_router(plano_controller.router)
app.include_router(trending_controller.router)
app.include_router(pagamento_controller.router)

# Endpoint WebSocket de Notificações e Chat com autenticação JWT estrita (BOLA / IDOR Protection)
@app.websocket("/ws")
@app.websocket("/ws/notificacoes")
@app.websocket("/ws/notificacoes/{user_id}")
@app.websocket("/ws/{user_id}")
async def websocket_notificacoes(
    websocket: WebSocket,
    user_id: Optional[int] = None,
    token: Optional[str] = Query(None)
):
    """
    Endpoint WebSocket blindado com autenticação JWT obrigatória via Query Parameter (?token=...).
    O user_id é extraído estritamente do payload assinado do token JWT, impedindo BOLA / IDOR.
    Se o token for ausente, expirado ou inválido, a conexão é encerrada com código 4001.
    """
    if not token:
        await websocket.close(code=4001, reason="Token de autenticação não fornecido.")
        return

    try:
        payload = validar_token_jwt(token, tipo_esperado="access")
        usuario_id_token_str = payload.get("sub")
        if not usuario_id_token_str:
            await websocket.close(code=4001, reason="Token inválido: sujeito ausente.")
            return
        auth_user_id = int(usuario_id_token_str)
    except Exception:
        await websocket.close(code=4001, reason="Token inválido ou expirado.")
        return

    # Conecta o WebSocket com o ID estritamente validado do token
    await manager.connect(websocket, auth_user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    payload_ws = json.loads(data)
                    tipo = str(payload_ws.get("tipo", "")).upper()
                    if tipo in ("DIGITANDO", "TYPING"):
                        conversa_id = payload_ws.get("conversa_id") or payload_ws.get("idConversa")
                        if conversa_id:
                            from app.database import SessionLocal
                            from app.repositories.conversa_repository import ConversaRepository
                            db_ws = SessionLocal()
                            try:
                                participantes = ConversaRepository.buscar_participantes(db_ws, int(conversa_id))
                                for p in participantes:
                                    if p.idUsuario != auth_user_id:
                                        await manager.send_personal_message(p.idUsuario, payload_ws)
                            finally:
                                db_ws.close()
                    elif tipo in ("MENSAGEM", "NOVA_MENSAGEM", "CHAT_MESSAGE"):
                        conversa_id = payload_ws.get("conversa_id") or payload_ws.get("idConversa")
                        conteudo = payload_ws.get("conteudo") or payload_ws.get("mensagem")
                        if conversa_id and conteudo:
                            from app.database import SessionLocal
                            from app.services.mensagem_service import MensagemService
                            from app.schemas.mensagem_schema import MensagemCriar
                            db_ws = SessionLocal()
                            try:
                                await MensagemService.enviar_mensagem(
                                    db=db_ws,
                                    remetente_id=auth_user_id,
                                    conversa_id=int(conversa_id),
                                    dados=MensagemCriar(conteudo=str(conteudo))
                                )
                            finally:
                                db_ws.close()
                except Exception:
                    pass
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket, auth_user_id)


# Servir arquivos estáticos (uploads de fotos de perfil, obras, certificados, etc.)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Endpoint de checagem de saúde
@app.get("/", tags=["Status"])
def read_root():
    return {
        "status": "Online",
        "projeto": "Artfolio API",
        "documentacao": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.APP_HOST, 
        port=settings.APP_PORT, 
        reload=settings.DEBUG
    )