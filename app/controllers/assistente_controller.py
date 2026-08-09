from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.schemas.assistente_schema import (
    AssistenteMensagemEnviar,
    AssistenteEnviarResposta,
    AssistenteConversaResposta,
    AssistenteConversaListaResposta,
)
from app.services.assistente_service import AssistenteService

router = APIRouter(prefix="/assistente", tags=["Assistente IA"])


@router.post("/mensagem", response_model=AssistenteEnviarResposta)
async def enviar_mensagem(
    dados: AssistenteMensagemEnviar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Envia uma mensagem ao assistente de IA.

    - Se `idConversa` for fornecido, continua a conversa existente.
    - Se omitido, cria uma nova conversa automaticamente.

    Retorna a resposta da IA junto com o ID da conversa para uso em
    mensagens subsequentes.
    """
    resultado = await AssistenteService.enviar_mensagem(
        db=db,
        id_usuario=usuario_atual.id,
        texto=dados.message,
        id_conversa=dados.idConversa,
    )
    return resultado


@router.get("/conversas", response_model=List[AssistenteConversaListaResposta])
def listar_conversas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Lista todas as conversas do usuário com o assistente de IA,
    ordenadas pela mais recente.
    """
    return AssistenteService.listar_conversas(db, usuario_atual.id)


@router.get("/conversas/{conversa_id}", response_model=AssistenteConversaResposta)
def buscar_conversa(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Busca uma conversa específica com todo o histórico de mensagens.
    O usuário só pode acessar suas próprias conversas.
    """
    return AssistenteService.buscar_conversa(db, conversa_id, usuario_atual.id)


@router.patch("/conversas/{conversa_id}/encerrar", response_model=AssistenteConversaListaResposta)
def encerrar_conversa(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Encerra (marca como inativa) uma conversa com o assistente.
    """
    return AssistenteService.encerrar_conversa(db, conversa_id, usuario_atual.id)


@router.delete("/conversas/{conversa_id}", status_code=204)
def deletar_conversa(
    conversa_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Realiza o soft delete de uma conversa e suas mensagens.
    """
    AssistenteService.deletar_conversa(db, conversa_id, usuario_atual.id)
