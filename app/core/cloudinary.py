import cloudinary
from app.core.config import settings

def init_cloudinary():
    """
    Inicializa a configuração global da SDK do Cloudinary com as credenciais do ambiente.
    """
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )

# Inicializa automaticamente no momento da importação do módulo
init_cloudinary()
