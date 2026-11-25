try:
    import cloudinary
except ImportError:
    cloudinary = None

from app.core.config import settings

def init_cloudinary():
    """
    Inicializa a configuração global da SDK do Cloudinary com as credenciais do ambiente se configuradas.
    """
    if cloudinary and settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        try:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
        except Exception:
            pass

# Inicializa automaticamente no momento da importação do módulo
init_cloudinary()
