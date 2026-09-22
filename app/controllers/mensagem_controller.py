import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.mensagem_schema import (
    ConversaResposta,
    MensagemResposta,
    MensagemCriar,
    MensagemEditar,
    DenunciaChatCriar,
    DenunciaChatResposta
)
from app.services.mensagem_service import MensagemService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from fastapi import UploadFile, File, HTTPException
from app.core.config import settings

router = APIRouter(prefix="/conversas", tags=["Conversas / Mensagens"])

@router.get("", response_model=List[ConversaResposta], status_code=status.HTTP_200_OK, summary="Listar conversas do usuário")
@router.get("/", response_model=List[ConversaResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_conversas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todas as conversas ativas do usuário logado.
    """
    return MensagemService.listar_conversas(db, usuario_atual.id)

@router.post("/usuario/{destinatario_id}", response_model=ConversaResposta, status_code=status.HTTP_200_OK, summary="Obter ou iniciar conversa com usuário")
def obter_ou_criar_conversa(
    destinatario_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a conversa com o usuário destinatário ou cria uma nova se ainda não existir.
    """
    return MensagemService.obter_ou_criar_conversa(db, usuario_atual.id, destinatario_id)

@router.post("/{conversa_id}/mensagens", response_model=MensagemResposta, status_code=status.HTTP_201_CREATED, summary="Enviar mensagem na conversa")
async def enviar_mensagem(
    conversa_id: int,
    dados: MensagemCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Envia uma nova mensagem na conversa indicada.
    """
    return await MensagemService.enviar_mensagem(db, usuario_atual.id, conversa_id, dados)

@router.post("/upload", status_code=status.HTTP_201_CREATED, summary="Fazer upload de anexo para mensagem de chat")
def upload_anexo_chat(
    arquivo: UploadFile = File(...),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Recebe um anexo para conversa (PDF, JPG, PNG, WEBP, ZIP, DOCX, MP4), salva em disco e retorna a URL pública.
    """
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    extensoes_permitidas = [".jpg", ".jpeg", ".png", ".webp", ".pdf", ".zip", ".docx", ".mp4"]
    if ext not in extensoes_permitidas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de arquivo não suportado ({ext}). Formatos permitidos: JPG, PNG, WEBP, PDF, ZIP, DOCX, MP4."
        )

    conteudo = arquivo.file.read()
    if len(conteudo) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo excede o tamanho máximo permitido de 15 MB."
        )

    pasta_conversas = os.path.join(settings.UPLOAD_DIR, "conversas")
    os.makedirs(pasta_conversas, exist_ok=True)
    nome_salvo = f"anexo_{usuario_atual.id}_{uuid.uuid4().hex[:8]}{ext}"
    caminho = os.path.join(pasta_conversas, nome_salvo)
    with open(caminho, "wb") as f:
        f.write(conteudo)

    return {"url": f"/uploads/conversas/{nome_salvo}", "nome": arquivo.filename}

@router.delete("/{conversa_id}/mensagens", status_code=status.HTTP_200_OK, summary="Limpar histórico de mensagens da conversa")
def limpar_conversa(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Oculta o histórico de mensagens da conversa exclusivamente para o usuário autenticado.
    """
    return MensagemService.limpar_conversa(db, usuario_atual.id, conversa_id)

@router.delete("/mensagens/{mensagem_id}", status_code=status.HTTP_200_OK, summary="Excluir mensagem para o usuário atual")
def deletar_mensagem(
    mensagem_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Oculta a mensagem individualmente apenas para o usuário autenticado.
    """
    return MensagemService.deletar_mensagem_individual(db, usuario_atual.id, mensagem_id)

@router.post("/mensagens/excluir-lote", status_code=status.HTTP_200_OK, summary="Excluir lote de mensagens para o usuário atual")
def deletar_mensagens_lote(
    dados: dict,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Oculta múltiplas mensagens apenas para o usuário autenticado.
    """
    ids = dados.get("mensagem_ids") or dados.get("ids") or []
    for msg_id in ids:
        try:
            MensagemService.deletar_mensagem_individual(db, usuario_atual.id, int(msg_id))
        except Exception:
            pass
    return {"message": f"{len(ids)} mensagens excluídas para você com sucesso."}

@router.patch("/mensagens/{mensagem_id}", response_model=MensagemResposta, status_code=status.HTTP_200_OK, summary="Editar mensagem")
async def editar_mensagem(
    mensagem_id: int,
    dados: MensagemEditar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Edita o conteúdo de uma mensagem enviada há no máximo 15 minutos pelo usuário autenticado.
    """
    return await MensagemService.editar_mensagem(db, usuario_atual.id, mensagem_id, dados)

@router.post("/denuncias", response_model=DenunciaChatResposta, status_code=status.HTTP_201_CREATED, summary="Registrar denúncia de conversa/usuário")
def registrar_denuncia_chat(
    dados: DenunciaChatCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra uma denúncia de moderação vinculada ao usuário logado (denunciante_id).
    """
    return MensagemService.criar_denuncia_chat(db, usuario_atual.id, dados)

@router.patch("/{conversa_id}/ler", status_code=status.HTTP_200_OK, summary="Marcar mensagens da conversa como lidas")
async def marcar_mensagens_como_lidas(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Marca todas as mensagens não lidas recebidas nesta conversa como lidas.
    """
    return await MensagemService.marcar_como_lida(db, usuario_atual.id, conversa_id)

# Router auxiliar com prefixo /chat para compatibilidade total com clientes frontend
chat_router = APIRouter(prefix="/chat", tags=["Chat / Mensagens"])

@chat_router.patch("/conversas/{conversa_id}/ler", status_code=status.HTTP_200_OK, summary="Marcar mensagens da conversa como lidas (alias /chat)")
async def marcar_mensagens_como_lidas_chat(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Marca todas as mensagens não lidas recebidas nesta conversa como lidas (rota alternativa com prefixo /chat).
    """
    return await MensagemService.marcar_como_lida(db, usuario_atual.id, conversa_id)

@chat_router.patch("/mensagens/{mensagem_id}", response_model=MensagemResposta, status_code=status.HTTP_200_OK, summary="Editar mensagem (alias /chat)")
async def editar_mensagem_chat(
    mensagem_id: int,
    dados: MensagemEditar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Edita o conteúdo de uma mensagem enviada há no máximo 15 minutos pelo usuário autenticado.
    """
    return await MensagemService.editar_mensagem(db, usuario_atual.id, mensagem_id, dados)

@chat_router.delete("/mensagens/{mensagem_id}", status_code=status.HTTP_200_OK, summary="Excluir mensagem para o usuário atual (alias /chat)")
def deletar_mensagem_chat(
    mensagem_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Oculta a mensagem individualmente apenas para o usuário autenticado.
    """
    return MensagemService.deletar_mensagem_individual(db, usuario_atual.id, mensagem_id)

@chat_router.post("/mensagens/excluir-lote", status_code=status.HTTP_200_OK, summary="Excluir lote de mensagens para o usuário atual (alias /chat)")
def deletar_mensagens_lote_chat(
    dados: dict,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Oculta múltiplas mensagens apenas para o usuário autenticado.
    """
    ids = dados.get("mensagem_ids") or dados.get("ids") or []
    for msg_id in ids:
        try:
            MensagemService.deletar_mensagem_individual(db, usuario_atual.id, int(msg_id))
        except Exception:
            pass
    return {"message": f"{len(ids)} mensagens excluídas para você com sucesso."}

@chat_router.post("/denuncias", response_model=DenunciaChatResposta, status_code=status.HTTP_201_CREATED, summary="Registrar denúncia de conversa/usuário (alias /chat)")
def registrar_denuncia_chat_alias(
    dados: DenunciaChatCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra uma denúncia de moderação vinculada ao usuário logado (denunciante_id).
    """
    return MensagemService.criar_denuncia_chat(db, usuario_atual.id, dados)

@chat_router.post("/{conversa_id}/mensagens", response_model=MensagemResposta, status_code=status.HTTP_201_CREATED, summary="Enviar mensagem na conversa (alias /chat)")
@chat_router.post("/conversas/{conversa_id}/mensagens", response_model=MensagemResposta, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def enviar_mensagem_chat_alias(
    conversa_id: int,
    dados: MensagemCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Envia uma nova mensagem na conversa indicada (rota alternativa com prefixo /chat).
    """
    return await MensagemService.enviar_mensagem(db, usuario_atual.id, conversa_id, dados)
