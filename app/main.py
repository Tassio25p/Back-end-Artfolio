#Bibliotecas
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.database import engine, Base
#Controllers
from app.controllers import (
    auth_controller,
    postagem_controller,
    artista_controller,
    usuario_controller,
    feed_controller,
    notificacao_controller,
    admin_controller,
    mensagem_controller,
)
#Modelos
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
from app.models.obra_salva_model import ObraSalva
from app.models.denuncia_model import Denuncia
from app.models.usuario_model import Usuario

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
            }
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
                    datacriacao TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_postagem_usuario_view UNIQUE (idpostagem, idusuario)
                );
            """))
            conn.commit()

        # Garantir coluna deletado_por em mensagem
        tabela_msg_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mensagem')"
        )).scalar()
        if tabela_msg_existe:
            col_del_existe = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'mensagem' AND column_name = 'deletado_por')"
            )).scalar()
            if not col_del_existe:
                conn.execute(text("ALTER TABLE mensagem ADD COLUMN deletado_por VARCHAR(255) DEFAULT ''"))
                conn.commit()
                print("[OK] Coluna 'deletado_por' adicionada com sucesso à tabela 'mensagem'.")


except Exception as e:
    import traceback
    print("[ERRO] ERRO AO SINCRONIZAR O BANCO:")
    traceback.print_exc()

#Criação da API
app = FastAPI(
    title="Artfolio API",
    description="Backend para a plataforma artística digital Artfolio.",
    version="1.0.0"
)

#Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores de controllers da aplicação
app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(postagem_controller.router)
app.include_router(artista_controller.router)
app.include_router(feed_controller.router)
app.include_router(notificacao_controller.router)
app.include_router(admin_controller.router)
app.include_router(mensagem_controller.router)

# Servir arquivos estáticos (uploads de fotos de perfil, obras, certificados, etc.)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

#Endpoint de checagem de saúde
@app.get("/", tags=["Status"])
def read_root():
    """
    Endpoint de checagem de saúde (Healthcheck) da API.
    """
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