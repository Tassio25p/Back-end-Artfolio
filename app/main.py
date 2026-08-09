import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from app.controllers import auth_controller, postagem_controller, artista_controller, assistente_controller, usuario_controller, feed_controller
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.assistente_conversa_model import AssistenteConversa
from app.models.assistente_mensagem_model import AssistenteMensagem
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.seguidor_model import Seguidor

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

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

app = FastAPI(
    title="Artfolio API",
    description="Backend para a plataforma artística digital Artfolio.",
    version="1.0.0"
)

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
