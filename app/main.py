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
    assistente_controller,
    usuario_controller,
    feed_controller,
    notificacao_controller,
    admin_controller,
)
#Modelos
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.assistente_conversa_model import AssistenteConversa
from app.models.assistente_mensagem_model import AssistenteMensagem
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.seguidor_model import Seguidor
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.models.obra_salva_model import ObraSalva
from app.models.denuncia_model import Denuncia

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "perfis"), exist_ok=True)
#Criação das tabelas
try:
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.connect() as conn:
        tabela_existe = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'usuario')"
        )).scalar()
        if tabela_existe:
            coluna_existe = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'usuario' AND column_name = 'tipo_conta')"
            )).scalar()
            if not coluna_existe:
                conn.execute(text(
                    "ALTER TABLE usuario ADD COLUMN tipo_conta VARCHAR(20) NOT NULL DEFAULT 'cliente'"
                ))
                conn.commit()
                print("✔ Coluna 'tipo_conta' adicionada com sucesso à tabela 'usuario'.")

            # Verificar e adicionar colunas de redes sociais para o módulo de edição de perfil
            colunas_perfil = {
                "instagram": "VARCHAR(255)",
                "behance": "VARCHAR(255)",
                "website": "VARCHAR(255)",
            }
            for coluna, tipo in colunas_perfil.items():
                coluna_perfil_existe = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = 'usuario' AND column_name = '{coluna}')"
                )).scalar()
                if not coluna_perfil_existe:
                    conn.execute(text(
                        f"ALTER TABLE usuario ADD COLUMN {coluna} {tipo}"
                    ))
                    conn.commit()
                    print(f"✔ Coluna '{coluna}' adicionada com sucesso à tabela 'usuario'.")
except Exception as e:
    print(f"Aviso: Não foi possível sincronizar o schema com o banco: {e}")
#Criação da API
app = FastAPI(
    title="Artfolio API",
    description="Backend para a plataforma artística digital Artfolio.",
    version="1.0.0"
)
#Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua pelo domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores de controllers da aplicação
app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(postagem_controller.router)
app.include_router(artista_controller.router)
app.include_router(assistente_controller.router)
app.include_router(feed_controller.router)
app.include_router(notificacao_controller.router)
app.include_router(admin_controller.router)


# Servir arquivos estáticos (uploads de fotos de perfil, obras, etc.)
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
    # Executa o servidor de desenvolvimento recarregando automaticamente ao alterar arquivos
    uvicorn.run(
        "app.main:app", 
        host=settings.APP_HOST, 
        port=settings.APP_PORT, 
        reload=settings.DEBUG
    )