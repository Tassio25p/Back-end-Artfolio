from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario_model import Usuario
from app.controllers.auth_controller import obter_usuario_atual
from app.schemas.pagamento_schema import (
    CriarCheckoutSessaoRequisicao,
    CriarCheckoutSessaoResposta
)
from app.services.pagamento_service import PagamentoService
from app.core.limiter import limiter

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos e Stripe"])

@router.post(
    "/criar-checkout-sessao",
    response_model=CriarCheckoutSessaoResposta,
    status_code=status.HTTP_200_OK,
    summary="Criar sessão de checkout no Stripe"
)
@limiter.limit("15/minute")
def criar_checkout_sessao(
    request: Request,
    dados: CriarCheckoutSessaoRequisicao,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Inicia uma sessão de checkout do Stripe em modo assinatura (subscription) para o usuário autenticado.
    Bloqueia usuários cujo e-mail ainda não tenha sido verificado (is_verified = False).
    Retorna a URL oficial do Stripe para onde o navegador do cliente deve ser redirecionado.
    """
    if not usuario_atual.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="É obrigatório verificar o seu endereço de e-mail antes de assinar um plano no Artfolio."
        )

    return PagamentoService.criar_checkout_sessao(db, usuario_atual, dados)

@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Webhook oficial para receber eventos assíncronos do Stripe"
)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint público do Webhook do Stripe.
    Escuta e valida assinaturas de eventos como checkout.session.completed para ativação automática
    de planos (Pro e Boost) na base de dados do Artfolio.
    """
    raw_payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    return PagamentoService.processar_webhook(db, raw_payload, sig_header)
