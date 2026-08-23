from logging.config import fileConfig
import os

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ============================================================
# CARREGAR VARIÁVEIS DO .env
# ============================================================

load_dotenv()

# ============================================================
# IMPORTAR CONFIGURAÇÃO DO SQLALCHEMY
# ============================================================

from app.database import Base

# ============================================================
# IMPORTAR TODOS OS MODELS
# ============================================================
# Esses imports são necessários para que o SQLAlchemy registre
# todas as tabelas no Base.metadata antes do Alembic comparar
# o código com o banco de dados.

from app.models.artista_model import Artista
from app.models.assinatura_model import Assinatura
from app.models.categoria_model import Categoria
from app.models.comentario_model import Comentario
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.curtida_model import Curtida
from app.models.denuncia_model import Denuncia
from app.models.log_model import Log
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.models.obra_salva_model import ObraSalva
from app.models.plano_model import Plano
from app.models.postagem_categoria_model import PostagemCategoria
from app.models.postagem_model import Postagem
from app.models.postagem_visualizacao_model import PostagemVisualizacao
from app.models.preferencia_usuario_model import PreferenciaUsuario
from app.models.seguidor_model import Seguidor
from app.models.usuario_model import Usuario


# ============================================================
# CONFIGURAÇÃO DO ALEMBIC
# ============================================================

config = context.config

# Configuração de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# CONEXÃO COM POSTGRESQL
# ============================================================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)


# ============================================================
# METADATA DOS MODELS
# ============================================================

target_metadata = Base.metadata


# ============================================================
# MIGRAÇÕES OFFLINE
# ============================================================

def run_migrations_offline() -> None:
    """Executa migrations sem abrir conexão direta com o banco."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# MIGRAÇÕES ONLINE
# ============================================================

def run_migrations_online() -> None:
    """Executa migrations utilizando conexão com PostgreSQL."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# EXECUTAR
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()