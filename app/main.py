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

from sqlalchemy import text

SUBCATEGORIAS_OFICIAIS = [
    "Pintura", "Desenho", "Ilustração Tradicional", "Ilustração Infantil", "Escultura", "Gravura", "Quadrinhos HQ",
    "Ilustração Digital", "Modelagem 3D", "Animação 2D", "Animação 3D", "Pixel Art", "Escultura Digital", "Voxel Art",
    "Artesanato", "Costura", "Crochê", "Amigurumi", "Tricô", "Tapeçaria", "Macramê", "Feltragem", "Tecelagem", "Bordado",
    "Escritura", "Poesia", "Romance", "Conto", "Crônica", "Roteirização", "Dramaturgia",
    "Cinema", "Fotografia", "Videoarte", "Edição de Vídeo", "Direção de Arte",
    "Teatro", "Dança", "Ópera", "Circo", "Performance", "Mímica",
    "Composição", "Canto", "Instrumentação", "Produção Musical", "Sonoplastia",
    "Arquitetura", "Desenho Técnico de Plantas Baixas", "Maquetaria", "Urbanismo", "Design de Interiores", "Paisagismo", "Jardinagem Artística",
    "Modificação", "Tatuagem", "Micropigmentação Artística", "Body Painting", "Pintura Corporal", "Maquiagem Artística FX",
    "Design Gráfico", "Web Design", "Design de Moda", "Joalheria", "Cerâmica", "Marcenaria"
]


def sincronizar_categorias(conn) -> None:
    """
    Semeia os Desafios Semanais e sincroniza todas as categorias oficiais do catálogo Artfolio,
    informando explicitamente todas as colunas NOT NULL da tabela 'categoria'.
    """
    qtd_desafios = conn.execute(
        text("SELECT COUNT(*) FROM categoria WHERE is_desafio = TRUE AND deletado = FALSE")
    ).scalar()
    if qtd_desafios == 0:
        conn.execute(text("""
            INSERT INTO categoria (nomecategoria, is_desafio, desafio_ativo, data_inicio_desafio, prazo_dias, deletado)
            VALUES
                ('Cyberpunk & Futurismo', TRUE, TRUE, CURRENT_TIMESTAMP, 7, FALSE),
                ('Retrofuturismo 80s', TRUE, FALSE, NULL, 7, FALSE),
                ('Natureza Viva & Botânica', TRUE, FALSE, NULL, 7, FALSE),
                ('Surrealismo Onírico', TRUE, FALSE, NULL, 7, FALSE),
                ('Fantasia Medieval Sombria', TRUE, FALSE, NULL, 7, FALSE),
                ('Arte Tradicional a Óleo', TRUE, FALSE, NULL, 7, FALSE),
                ('Sci-Fi & Espaço Profundo', TRUE, FALSE, NULL, 7, FALSE)
        """))
        conn.commit()
        print("[OK] Temas oficiais de Desafios Semanais semeados com sucesso na tabela 'categoria'.")

    for cat_nome in SUBCATEGORIAS_OFICIAIS:
        existe = conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM categoria WHERE LOWER(nomecategoria) = LOWER(:nome))"),
            {"nome": cat_nome},
        ).scalar()
        if not existe:
            conn.execute(
                text(
                    "INSERT INTO categoria (nomecategoria, is_desafio, desafio_ativo, prazo_dias, deletado) "
                    "VALUES (:nome, FALSE, FALSE, 7, FALSE)"
                ),
                {"nome": cat_nome},
            )
    conn.commit()
    print("[OK] Categorias e subcategorias oficiais do catálogo sincronizadas com sucesso.")


# Criação das tabelas e auto-migração do esquema no PostgreSQL
try:
    Base.metadata.create_all(bind=engine)
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

            # Garantir que senha aceite NULL para anonimização LGPD na exclusão de conta e login OAuth
            try:
                conn.execute(text("ALTER TABLE usuario ALTER COLUMN senha DROP NOT NULL"))
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

            # Garante que todos os usuários fiquem verificados para ambiente de desenvolvimento local
            try:
                conn.execute(text("UPDATE usuario SET is_verified = TRUE WHERE is_verified IS FALSE OR is_verified IS NULL"))
                conn.commit()
                print("[OK] Todos os usuários foram verificados (is_verified = TRUE) com sucesso!")
            except Exception:
                pass

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

        # Garantir sementes dos Desafios Semanais rotativos (Art Prompts) e catálogo oficial
        tabela_cat_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'categoria')"
        )).scalar()
        if tabela_cat_existe:
            for col_cat, tipo_cat in [
                ("is_desafio", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("desafio_ativo", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("data_inicio_desafio", "TIMESTAMP"),
                ("prazo_dias", "INTEGER NOT NULL DEFAULT 7"),
                ("data_fim_desafio", "TIMESTAMP"),
            ]:
                col_cat_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'categoria' AND column_name = '{col_cat}')"
                )).scalar()
                if not col_cat_existe:
                    conn.execute(text(f"ALTER TABLE categoria ADD COLUMN {col_cat} {tipo_cat}"))
                    conn.commit()
                    print(f"[OK] Coluna '{col_cat}' adicionada com sucesso à tabela 'categoria'.")

            sincronizar_categorias(conn)

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


async def rotina_rotacao_desafios_semanais():
    """
    Rotina em background que verifica periodicamente e rotaciona o Desafio Semanal (Art Prompt) a cada 7 dias.
    """
    try:
        while True:
            try:
                from datetime import datetime, timezone, timedelta
                db = SessionLocal()
                try:
                    desafios = db.query(Categoria).filter(
                        Categoria.deletado == False,
                        Categoria.is_desafio == True
                    ).order_by(Categoria.id.asc()).all()

                    if desafios:
                        ativo = next((d for d in desafios if d.desafio_ativo), None)
                        agora = datetime.now(timezone.utc)
                        precisa_rotacionar = False

                        if not ativo or not ativo.data_inicio_desafio:
                            precisa_rotacionar = True
                        else:
                            inicio = ativo.data_inicio_desafio
                            if inicio.tzinfo is None:
                                inicio = inicio.replace(tzinfo=timezone.utc)
                            prazo = getattr(ativo, "prazo_dias", 7) or 7
                            fim_previsto = getattr(ativo, "data_fim_desafio", None)
                            if fim_previsto:
                                if fim_previsto.tzinfo is None:
                                    fim_previsto = fim_previsto.replace(tzinfo=timezone.utc)
                                if agora >= fim_previsto:
                                    precisa_rotacionar = True
                            elif agora - inicio >= timedelta(days=prazo):
                                precisa_rotacionar = True

                        if precisa_rotacionar:
                            # Desativa o desafio atual
                            for d in desafios:
                                d.desafio_ativo = False
                            
                            # Escolhe o próximo da fila circular
                            proximo = None
                            if ativo:
                                proximo = next((d for d in desafios if d.id > ativo.id), None)
                            if not proximo:
                                proximo = desafios[0]

                            prazo_proximo = getattr(proximo, "prazo_dias", 7) or 7
                            proximo.desafio_ativo = True
                            proximo.data_inicio_desafio = agora
                            proximo.data_fim_desafio = agora + timedelta(days=prazo_proximo)
                            db.commit()
                            print(f"[Desafios Semanais] Novo desafio ativado com sucesso: '{proximo.nomeCategoria}' (ID #{proximo.id}).")
                finally:
                    db.close()
            except Exception as e:
                print(f"[Desafios Semanais] Erro na rotação: {e}")
            await asyncio.sleep(3600)  # Checa a cada 1 hora
    except asyncio.CancelledError:
        print("[Desafios Semanais] Rotina encerrada com sucesso.")


# Conjunto global para guardar referências fortes das tarefas e evitar o Garbage Collector
tarefas_background = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: registra loop principal para fallback WebSocket e inicializa rotinas
    manager.set_loop(asyncio.get_running_loop())
    task_trending = asyncio.create_task(rotina_atualizacao_trending())
    task_redis = asyncio.create_task(iniciar_subscriber_redis())
    task_desafios = asyncio.create_task(rotina_rotacao_desafios_semanais())
    
    tarefas_background.add(task_trending)
    tarefas_background.add(task_redis)
    tarefas_background.add(task_desafios)
    
    task_trending.add_done_callback(tarefas_background.discard)
    task_redis.add_done_callback(tarefas_background.discard)
    task_desafios.add_done_callback(tarefas_background.discard)
    
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


@app.get("/uploads/certificados/{filename:path}", include_in_schema=False)
def servir_certificado_portfolio(filename: str, download: Optional[str] = Query(None), filename_dl: Optional[str] = Query(None, alias="filename")):
    """
    Serve documentos de portfólio e certificados com suporte a visualização inline no navegador
    e download direto, garantindo fallback caso o arquivo físico não seja encontrado no diretório atual.
    """
    from fastapi.responses import FileResponse, Response

    nome_seguro = os.path.basename(filename)
    base_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidatos = [
        os.path.join(settings.UPLOAD_DIR, "certificados", nome_seguro),
        os.path.join(base_backend_dir, "uploads", "certificados", nome_seguro),
    ]

    caminho_encontrado = next((p for p in candidatos if os.path.exists(p)), None)

    if not caminho_encontrado and nome_seguro.lower().endswith(".pdf"):
        # Fallback automático: reconstrói o PDF com os metadados do certificado cadastrado no banco
        titulo_doc = "Certificado / Portfolio Artistico"
        instituicao_doc = "Artfolio"
        ano_doc = "2026"
        artista_doc = "Artista Artfolio"
        nome_original = filename_dl or nome_seguro

        from app.database import SessionLocal
        db_cert = SessionLocal()
        try:
            rows = db_cert.execute(
                text("SELECT nome, certificados FROM usuario WHERE certificados IS NOT NULL")
            ).fetchall()
            for r in rows:
                if r.certificados and nome_seguro in r.certificados:
                    artista_doc = r.nome or artista_doc
                    try:
                        lista_c = json.loads(r.certificados)
                        for item_c in lista_c:
                            if nome_seguro in str(item_c.get("arquivoUrl", "")):
                                titulo_doc = item_c.get("titulo") or titulo_doc
                                instituicao_doc = item_c.get("instituicao") or instituicao_doc
                                ano_doc = str(item_c.get("ano") or ano_doc)
                                nome_original = item_c.get("nomeArquivo") or nome_original
                                break
                    except Exception:
                        pass
                    break
        except Exception:
            pass
        finally:
            db_cert.close()

        def _esc_pdf(val: str) -> str:
            s = (val or "").encode("latin-1", errors="replace").decode("latin-1")
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        stream_bytes = (
            "BT\n"
            "/F1 20 Tf\n"
            "72 720 Td\n"
            "(ARTFOLIO - CERTIFICADO & PORTFOLIO ARTISTICO) Tj\n"
            "/F1 15 Tf\n"
            "0 -45 Td\n"
            f"(Titulo: {_esc_pdf(titulo_doc)}) Tj\n"
            "/F1 12 Tf\n"
            "0 -28 Td\n"
            f"(Instituicao / Emissor: {_esc_pdf(instituicao_doc)}) Tj\n"
            "0 -24 Td\n"
            f"(Ano: {_esc_pdf(ano_doc)}) Tj\n"
            "0 -24 Td\n"
            f"(Artista: {_esc_pdf(artista_doc)}) Tj\n"
            "0 -24 Td\n"
            f"(Arquivo: {_esc_pdf(nome_original)}) Tj\n"
            "ET\n"
        ).encode("latin-1")

        objs = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
            f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1") + stream_bytes + b"endstream\nendobj\n",
        ]
        pdf_buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for o in objs:
            offsets.append(len(pdf_buf))
            pdf_buf.extend(o)
        xref_pos = len(pdf_buf)
        pdf_buf.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("latin-1"))
        for off in offsets:
            pdf_buf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
        pdf_buf.extend(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1"))

        destino_padrao = os.path.join(base_backend_dir, "uploads", "certificados", nome_seguro)
        try:
            os.makedirs(os.path.dirname(destino_padrao), exist_ok=True)
            with open(destino_padrao, "wb") as f:
                f.write(pdf_buf)
            caminho_encontrado = destino_padrao
        except Exception:
            disposition = "attachment" if str(download).lower() in ("1", "true") else "inline"
            return Response(
                content=bytes(pdf_buf),
                media_type="application/pdf",
                headers={"Content-Disposition": f'{disposition}; filename="{nome_seguro}"'}
            )

    if not caminho_encontrado or not os.path.exists(caminho_encontrado):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Arquivo de portfólio ou certificado não encontrado.")

    ext = os.path.splitext(nome_seguro)[1].lower()
    media_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    is_download = str(download).lower() in ("1", "true")
    nome_download = (filename_dl or nome_seguro).replace('"', "")
    disposition_type = "attachment" if is_download else "inline"

    return FileResponse(
        path=caminho_encontrado,
        media_type=media_type,
        filename=nome_download if is_download else None,
        content_disposition_type=disposition_type,
    )


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