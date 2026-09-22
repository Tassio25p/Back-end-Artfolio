from pydantic import BaseModel, Field
from typing import Optional

class CriarCheckoutSessaoRequisicao(BaseModel):
    """
    Schema para requisição de criação de sessão de Checkout no Stripe.
    Pode receber o price_id diretamente ou plano_id/plano_tipo para resolução automática.
    """
    price_id: Optional[str] = Field(None, description="Stripe Price ID correspondente ao plano (ex: price_1xxx)")
    plano_id: Optional[int] = Field(None, description="ID do plano cadastrado no banco (2=Pro, 3=Boost)")
    plano_tipo: Optional[str] = Field(None, description="Tipo do plano ('Pro' ou 'Boost')")

class CriarCheckoutSessaoResposta(BaseModel):
    """
    Schema de resposta com a URL de checkout hospedada do Stripe para redirecionamento.
    """
    checkout_url: str = Field(..., description="URL oficial do Stripe Checkout")
    session_id: str = Field(..., description="ID da sessão criada no Stripe")
