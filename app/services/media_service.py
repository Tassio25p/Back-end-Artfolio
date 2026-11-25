import os
import uuid
from typing import Any
from fastapi import HTTPException, status, UploadFile
try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    cloudinary: Any = None
from app.core.cloudinary import init_cloudinary
from app.core.config import settings

FORMATOS_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".bmp", ".avif"}
FORMATOS_VIDEO = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
FORMATOS_DOC = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".odt", ".rtf"}
FORMATOS_3D_DESIGN = {".obj", ".fbx", ".gltf", ".glb", ".stl", ".blend", ".dae", ".zip", ".rar", ".psd", ".ai"}

FORMATOS_PERMITIDOS = FORMATOS_IMAGEM | FORMATOS_VIDEO | FORMATOS_DOC | FORMATOS_3D_DESIGN

MIME_TYPES_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/avif": ".avif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "application/vnd.oasis.opendocument.text": ".odt",
    "application/rtf": ".rtf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/x-rar-compressed": ".rar",
    "image/vnd.adobe.photoshop": ".psd",
    "application/postscript": ".ai",
    "application/octet-stream": ".bin",
    "model/gltf-binary": ".glb",
    "model/gltf+json": ".gltf",
    "model/stl": ".stl",
}

class MediaService:
    """
    Serviço centralizado para validação e upload de mídias/imagens/documentos/vídeos/3D
    no Cloudinary com fallback automático para armazenamento local.
    """

    @staticmethod
    def _validar_magic_bytes(conteudo: bytes, ext: str = "") -> bool:
        """
        Valida a assinatura binária ou permite extensões suportadas.
        """
        if len(conteudo) < 4:
            return False
        # JPEG
        if conteudo.startswith(b"\xff\xd8\xff"):
            return True
        # PNG
        if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        # GIF
        if conteudo.startswith(b"GIF87a") or conteudo.startswith(b"GIF89a"):
            return True
        # WEBP
        if len(conteudo) >= 12 and conteudo.startswith(b"RIFF") and conteudo[8:12] == b"WEBP":
            return True
        # PDF
        if conteudo.startswith(b"%PDF"):
            return True
        # ZIP / DOCX / PPTX
        if conteudo.startswith(b"PK\x03\x04"):
            return True
        # RAR
        if conteudo.startswith(b"Rar!\x1a\x07"):
            return True
        # MP4 / MOV / QuickTime
        if len(conteudo) >= 12 and (conteudo[4:8] == b"ftyp" or conteudo.startswith(b"\x00\x00\x00")):
            return True
        # WEBM / MKV
        if conteudo.startswith(b"\x1a\x45\xdf\xa3"):
            return True
        # PSD
        if conteudo.startswith(b"8BPS"):
            return True
        # SVG / XML / TXT / 3D textual formats
        ext_lower = ext.lower()
        if ext_lower in {".svg", ".txt", ".obj", ".gltf", ".dae", ".blend", ".fbx", ".stl", ".glb", ".doc", ".ppt", ".odt", ".rtf", ".ai"}:
            return True
        return True

    @staticmethod
    def upload_imagem(
        arquivo: UploadFile,
        folder: str = "artfolio/postagens",
        max_size_mb: int = 10
    ) -> str:
        """
        Valida o formato, magic bytes e tamanho do arquivo enviado e realiza o upload seguro para o Cloudinary
        ou para o disco local se as credenciais do Cloudinary não estiverem preenchidas.
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
                detail=f"Formato de arquivo '{ext}' não suportado. Formatos permitidos: Imagens, Vídeos, Documentos (PDF, DOC, PPT), 3D (OBJ, FBX, GLTF, BLEND, STL) e ZIP."
            )

        # 2. Leitura do conteúdo e validação de tamanho e Magic Bytes
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

        # Validação de assinatura binária de segurança (Magic Bytes)
        if not MediaService._validar_magic_bytes(conteudo, ext):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo corrompido ou formato incompatível com a extensão informada."
            )

        max_bytes = max_size_mb * 1024 * 1024
        if len(conteudo) > max_bytes:
            tamanho_mb_real = len(conteudo) / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"O arquivo enviado possui {tamanho_mb_real:.1f}MB e excede o limite máximo permitido de {max_size_mb}MB para o seu plano. Faça upgrade para ter limites maiores (Pro: até 50MB, Boost: até 100MB)!"
            )

        # 3. Realizar upload no Cloudinary (se configurado) ou fallback para armazenamento local
        tem_cloudinary = bool(
            cloudinary and
            settings.CLOUDINARY_CLOUD_NAME and
            settings.CLOUDINARY_API_KEY and
            settings.CLOUDINARY_API_SECRET
        )

        if tem_cloudinary:
            try:
                init_cloudinary()
                
                # Para imagens estáticas aplicamos fetch_format/quality, para GIFs preservamos animação
                is_gif = ext == ".gif" or mime_type == "image/gif"
                is_pure_image = ext in FORMATOS_IMAGEM and not is_gif
                upload_params: dict[str, Any] = {
                    "folder": folder,
                    "resource_type": "image" if (is_pure_image or is_gif) else "auto",
                }
                if is_pure_image:
                    upload_params["transformation"] = [{"fetch_format": "auto", "quality": "auto"}]
                elif is_gif:
                    upload_params["format"] = "gif"
                    upload_params["flags"] = "animated"

                assert cloudinary is not None
                resposta = cloudinary.uploader.upload(
                    conteudo,
                    **upload_params
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
        else:
            # Fallback seguro para armazenamento local no servidor preservando GIF
            try:
                is_gif = ext == ".gif" or mime_type == "image/gif"
                extensao = ext if ext in FORMATOS_PERMITIDOS else (".gif" if is_gif else ".png")
                nome_unico = f"{uuid.uuid4().hex}{extensao}"

                # Extrai subpasta de destino (ex: 'postagens' ou 'perfis')
                subpasta = folder.split("/")[-1] if "/" in folder else folder
                pasta_destino = os.path.join(settings.UPLOAD_DIR, subpasta)
                os.makedirs(pasta_destino, exist_ok=True)

                caminho_arquivo = os.path.join(pasta_destino, nome_unico)
                with open(caminho_arquivo, "wb") as f:
                    f.write(conteudo)

                return f"/uploads/{subpasta}/{nome_unico}"
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Falha ao salvar imagem localmente: {str(e)}"
                )

    @staticmethod
    def upload_documento(
        arquivo: UploadFile,
        folder: str = "artfolio/certificados",
        max_size_mb: int = 10
    ) -> str:
        """
        Valida formato (PDF ou Imagens), magic bytes e tamanho de documento ou certificado,
        realizando upload seguro no Cloudinary ou fallback local.
        """
        if not arquivo or not arquivo.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum arquivo válido foi fornecido."
            )

        ext = os.path.splitext(arquivo.filename)[1].lower()
        formatos_validos = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
        if ext not in formatos_validos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de documento não suportado. Formatos permitidos: PDF, JPG, PNG ou WEBP."
            )

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

        if not MediaService._validar_magic_bytes(conteudo):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo corrompido ou formato binário incompatível com a extensão informada."
            )

        max_bytes = max_size_mb * 1024 * 1024
        if len(conteudo) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O documento excede o tamanho máximo permitido de {max_size_mb}MB."
            )

        # Sempre persiste cópia local para garantir visualização e download diretos sem bloqueio de PDF externo
        nome_unico = f"{uuid.uuid4().hex}{ext}"
        subpasta = folder.split("/")[-1] if "/" in folder else folder
        pasta_destino = os.path.join(settings.UPLOAD_DIR, subpasta)
        os.makedirs(pasta_destino, exist_ok=True)
        caminho_arquivo = os.path.join(pasta_destino, nome_unico)
        url_local = f"/uploads/{subpasta}/{nome_unico}"

        try:
            with open(caminho_arquivo, "wb") as f:
                f.write(conteudo)
        except Exception as e:
            if ext == ".pdf":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Falha ao salvar documento localmente: {str(e)}"
                )

        # Para arquivos PDF, servir sempre pelo endpoint local para suportar visualização inline e download direto
        if ext == ".pdf":
            return url_local

        tem_cloudinary = bool(
            cloudinary and
            settings.CLOUDINARY_CLOUD_NAME and
            settings.CLOUDINARY_API_KEY and
            settings.CLOUDINARY_API_SECRET
        )

        if tem_cloudinary:
            try:
                init_cloudinary()
                assert cloudinary is not None
                resposta = cloudinary.uploader.upload(
                    conteudo,
                    folder=folder,
                    resource_type="image"
                )
                secure_url = resposta.get("secure_url")
                if secure_url:
                    return secure_url
            except Exception:
                pass

        if os.path.exists(caminho_arquivo):
            return url_local

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível armazenar o documento enviado."
        )


