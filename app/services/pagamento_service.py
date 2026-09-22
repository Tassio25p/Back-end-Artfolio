import json
import logging
from typing import Optional
import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usuario_model import Usuario
from app.models.plano_model import Plano
from app.schemas.pagamento_schema import CriarCheckoutSessaoRequisicao
from app.services.plano_service import PlanoService

logger = logging.getLogger(__name__)

class PagamentoService:
    """
    Serviço responsável pela integração com o Stripe Checkout e processamento de Webhooks.
    """

    @staticmethod
    def criar_checkout_sessao(
        db: Session,
        usuario: Usuario,
        dados: CriarCheckoutSessaoRequisicao
    ) -> dict:
        """
        Cria uma sessão de Checkout hospedada no Stripe em modo de subscrição recorrente (subscription).
        Associa o client_reference_id com o ID do usuário autenticado e retorna a URL de redirecionamento.
        """
        if not getattr(usuario, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="É obrigatório verificar o seu endereço de e-mail antes de assinar um plano no Artfolio."
            )

        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A chave secreta da API do Stripe (STRIPE_SECRET_KEY) não está configurada no servidor (.env)."
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

        # Determinar plano e tipo
        plano = None
        if dados.plano_id:
            plano = db.query(Plano).filter(Plano.id == dados.plano_id, Plano.deletado == False).first()
        elif dados.plano_tipo:
            plano = db.query(Plano).filter(Plano.tipo.ilike(f"%{dados.plano_tipo.strip()}%"), Plano.deletado == False).first()

        plano_id = plano.id if plano else dados.plano_id
        plano_tipo = str(plano.tipo) if (plano and plano.tipo is not None) else (dados.plano_tipo or "Pro")

        # Determinar o Price ID do Stripe
        price_id = dados.price_id
        if not price_id or not price_id.strip():
            if plano_tipo and "boost" in plano_tipo.lower():
                price_id = settings.STRIPE_PRICE_ID_BOOST
            else:
                price_id = settings.STRIPE_PRICE_ID_PRO

        if not price_id or not price_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O identificador de preço do Stripe (price_id) não foi informado na requisição nem configurado no .env."
            )

        frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id.strip(),
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                client_reference_id=str(usuario.id),
                customer_email=str(usuario.email),
                metadata={
                    "usuario_id": str(usuario.id),
                    "plano_id": str(plano_id or ""),
                    "tipo_plano": str(plano_tipo or ""),
                },
                success_url=f"{frontend_url}/planos?sucesso=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/planos?cancelado=true",
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
        except stripe.StripeError as e:
            logger.error(f"[Stripe] Erro ao criar Checkout Session: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao comunicar com o Stripe: {str(e.user_message or e)}"
            )
        except Exception as e:
            logger.error(f"[Stripe] Erro inesperado: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Não foi possível iniciar a sessão de pagamento: {str(e)}"
            )

    @staticmethod
    def processar_webhook(
        db: Session,
        raw_payload: bytes,
        sig_header: Optional[str]
    ) -> dict:
        """
        Valida a assinatura criptográfica do Stripe Webhook e processa o evento de ativação de assinatura.
        """
        webhook_secret = (settings.STRIPE_WEBHOOK_SECRET or "").strip()
        event = None

        if webhook_secret and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload=raw_payload,
                    sig_header=sig_header,
                    secret=webhook_secret
                )
            except stripe.SignatureVerificationError as e:
                logger.warning(f"[Stripe Webhook] Assinatura inválida: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assinatura inválida do webhook Stripe (SignatureVerificationError)."
                )
            except Exception as e:
                logger.error(f"[Stripe Webhook] Falha no payload: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Falha ao validar evento do webhook: {str(e)}"
                )
        else:
            try:
                event = json.loads(raw_payload.decode("utf-8"))
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payload JSON inválido: {str(e)}"
                )

        if isinstance(event, stripe.Event):
            event_dict = event.to_dict()
        elif isinstance(event, dict):
            event_dict = event
        elif hasattr(event, "to_dict"):
            event_dict = event.to_dict()
        else:
            event_dict = {}

        event_type = event_dict.get("type")
        logger.info(f"[Stripe Webhook] Evento recebido: {event_type}")

        if event_type == "checkout.session.completed":
            data_obj = event_dict.get("data", {})
            session_obj = data_obj.get("object", {})
            if hasattr(session_obj, "to_dict"):
                session_obj = session_obj.to_dict()

            client_ref = session_obj.get("client_reference_id")
            metadata = session_obj.get("metadata") or {}
            user_id_raw = client_ref or metadata.get("usuario_id")

            if not user_id_raw:
                logger.warning("[Stripe Webhook] checkout.session.completed recebido sem identificador de usuário.")
                return {"status": "ignorado", "motivo": "usuario_id_ausente"}

            usuario_id = int(user_id_raw)
            plano_id_raw = metadata.get("plano_id")
            plano_id = int(plano_id_raw) if plano_id_raw and str(plano_id_raw).isdigit() else None
            tipo_plano = metadata.get("tipo_plano")
            subscription_id = session_obj.get("subscription")
            customer_id = session_obj.get("customer")

            PlanoService.ativar_assinatura_stripe(
                db=db,
                usuario_id=usuario_id,
                plano_id=plano_id,
                tipo_plano=tipo_plano,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id
            )

            logger.info(f"[Stripe Webhook] Assinatura do usuário {usuario_id} ativada com sucesso ({tipo_plano}).")
            return {"status": "sucesso", "evento": event_type, "usuario_id": usuario_id}

        return {"status": "sucesso", "evento": event_type, "mensagem": "Evento registrado sem ações adicionais."}
