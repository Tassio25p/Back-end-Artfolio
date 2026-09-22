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
    REDIS_PORT: int = 16379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Configurações de Segurança e JWT
    JWT_SECRET_KEY: str = "9476cf647ea376a9172f3a9e3381a179ceb6cf6a27e7f1e63a129d2f23ea6e61"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATA_ENCRYPTION_KEY: str = "9476cf647ea376a9172f3a9e3381a179ceb6cf6a27e7f1e63a129d2f23ea6e61"

    # Diretórios
    UPLOAD_DIR: str = "uploads"

    # Configurações do Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Configuração do Google OAuth2
    GOOGLE_CLIENT_ID: str = ""

    # Configurações do Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    STRIPE_PRICE_ID_BOOST: str = ""
    FRONTEND_URL: str = "http://localhost:5173"

    # Configurações do Brevo (Envio Transacional de E-mail)
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME")

    # Configuração de leitura de arquivos .env
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """
        Gera a URL de conexão com o banco de dados PostgreSQL.

        Monta a string de conexão síncrona usando psycopg2.
        """
        # Adicionado o '+psycopg2' aqui:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Instância única para importação em todo o projeto
settings = Settings()
