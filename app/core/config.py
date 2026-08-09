import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configurações globais do sistema.

    Esta classe lê as variáveis do arquivo .env e expõe
    as propriedades necessárias para a conexão com o banco de dados,
    Redis, segurança JWT e diretórios locais.
    """
    # Configurações do Servidor
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Configurações do PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "dbver"

    # Configurações do Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Configurações de Segurança e JWT
    JWT_SECRET_KEY: str = "9476cf647ea376a9172f3a9e3381a179ceb6cf6a27e7f1e63a129d2f23ea6e61"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Diretórios
    UPLOAD_DIR: str = "uploads"

    # Configuração de leitura de arquivos .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """
        Gera a URL de conexão com o banco de dados PostgreSQL.

        Monta a string de conexão síncrona usando psycopg2.
        """
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Instância única para importação em todo o projeto
settings = Settings()
