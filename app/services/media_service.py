import os
from fastapi import HTTPException, status, UploadFile
import cloudinary.uploader
from app.core.cloudinary import init_cloudinary

FORMATOS_PERMITIDOS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_TYPES_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

class MediaService:
    """
    Serviço centralizado para validação e upload de mídias/imagens no Cloudinary.
    """

    @staticmethod
    def upload_imagem(
        arquivo: UploadFile,
        folder: str = "artfolio/postagens",
        max_size_mb: int = 10
    ) -> str:
        """
        Valida o formato e tamanho da imagem enviada e realiza o upload seguro para o Cloudinary.
        
        :param arquivo: Objeto UploadFile do FastAPI
        :param folder: Pasta de destino no Cloudinary (ex: 'artfolio/postagens' ou 'artfolio/perfis')
        :param max_size_mb: Tamanho máximo permitido em Megabytes
        :return: String contendo a secure_url do Cloudinary
        """
        if not arquivo or not arquivo.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum arquivo válido foi fornecido."
            )

        ext = os.path.splitext(arquivo.filename)[1].lower()
        mime_type = (arquivo.content_type or "").lower()

        # 1. Validação de formato (Extensão ou MIME type)
        if ext not in FORMATOS_PERMITIDOS and mime_type not in MIME_TYPES_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem não suportado. Formatos permitidos: PNG, JPG, JPEG ou WEBP."
            )

        # 2. Leitura do conteúdo e validação de tamanho
        try:
            conteudo = arquivo.file.read()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível processar a leitura do arquivo enviado."
            )

        if not conteudo or len(conteudo) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado está vazio."
            )

        max_bytes = max_size_mb * 1024 * 1024
        if len(conteudo) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O arquivo excede o limite máximo permitido de {max_size_mb}MB."
            )

        # 3. Realizar upload no Cloudinary
        try:
            init_cloudinary()
            
            resposta = cloudinary.uploader.upload(
                conteudo,
                folder=folder,
                resource_type="image",
                transformation=[
                    {"fetch_format": "auto", "quality": "auto"}
                ]
            )

            secure_url = resposta.get("secure_url")
            if not secure_url:
                raise Exception("A resposta do Cloudinary não retornou a URL segura ('secure_url').")

            return secure_url

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha ao realizar upload para o Cloudinary: {str(e)}"
            )
