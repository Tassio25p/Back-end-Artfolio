from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

# Criação da Engine do SQLAlchemy para PostgreSQL
# O pool_pre_ping=True ajuda a evitar erros de conexões desconectadas/inativas
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True
)

# Fábrica de sessões para comunicação direta com o banco de dados
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Classe base para os modelos SQLAlchemy do banco de dados (SQLAlchemy 2.0)
class Base(DeclarativeBase):
    pass

def get_db():
    """
    Provedor de conexão com o banco de dados (Dependency Injection).

    Esta função geradora abre uma sessão com o banco de dados PostgreSQL
    para ser usada durante o processamento da requisição e garante que ela
    seja fechada automaticamente ao final, mesmo em caso de erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
