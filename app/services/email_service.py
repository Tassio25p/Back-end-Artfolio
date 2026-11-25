import os
import secrets
import logging
import requests
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def gerar_codigo_otp(tamanho: int = 6) -> str:
    """
    Gera um código OTP numérico criptograficamente seguro com a quantidade de dígitos especificada.
    Por padrão gera 6 dígitos (ex: '482910').
    """
    if tamanho <= 0:
        tamanho = 6
    # Garante um número exato de dígitos entre 10^(n-1) e 10^n - 1
    minimo = 10 ** (tamanho - 1)
    maximo = (10 ** tamanho) - 1
    return str(secrets.randbelow(maximo - minimo + 1) + minimo)


def construir_template_email_otp(nome: str, codigo_otp: str) -> str:
    """
    Constrói um template HTML moderno, elegante e responsivo para envio do código de verificação.
    Utiliza a identidade visual do Artfolio (tons escuros e acento degradê laranja/roxo).
    """
    primeiro_nome = nome.strip().split(" ")[0] if nome else "Artista"
    
    # Formatação com espaçamento entre os dígitos para máxima legibilidade
    otp_formatado = " ".join(list(codigo_otp))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de Verificação - Artfolio</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f1117; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #ffffff;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0f1117; padding: 40px 15px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 540px; background-color: #171923; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);" cellspacing="0" cellpadding="0" border="0">
                    
                    <!-- Header com Gradiente Artfolio -->
                    <tr>
                        <td style="padding: 35px 35px 25px; text-align: center; background: linear-gradient(135deg, rgba(255, 121, 63, 0.15) 0%, rgba(108, 92, 231, 0.15) 100%); border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
                            <h1 style="margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(135deg, #FF793F, #FF5252); -webkit-background-clip: text; -webkit-text-fill-color: #FF793F; display: inline-block;">
                                Artfolio
                            </h1>
                            <p style="margin: 8px 0 0; font-size: 14px; color: #a0aec0; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
                                Verificação de Conta
                            </p>
                        </td>
                    </tr>

                    <!-- Corpo Principal -->
                    <tr>
                        <td style="padding: 35px 35px 30px;">
                            <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e2e8f0;">
                                Olá, <strong style="color: #ffffff;">{primeiro_nome}</strong>!
                            </p>
                            <p style="margin: 0 0 28px; font-size: 15px; line-height: 1.6; color: #a0aec0;">
                                Obrigado por se juntar à comunidade de criadores do <strong>Artfolio</strong>. Utilize o código de verificação abaixo para confirmar seu endereço de e-mail e ativar todos os recursos da sua conta:
                            </p>

                            <!-- Bloco Visual do Código OTP -->
                            <div style="background-color: #0d0f15; border: 2px dashed #FF793F; border-radius: 12px; padding: 24px 16px; text-align: center; margin: 0 0 28px;">
                                <div style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; color: #ffffff; letter-spacing: 10px; margin-left: 10px;">
                                    {otp_formatado}
                                </div>
                                <p style="margin: 10px 0 0; font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 1px;">
                                    Código válido para verificação
                                </p>
                            </div>

                            <p style="margin: 0 0 12px; font-size: 14px; line-height: 1.5; color: #a0aec0;">
                                <strong style="color: #ed8936;">Atenção:</strong> Por motivos de segurança, nunca compartilhe este código com ninguém. Nossa equipe nunca solicitará seu código de verificação.
                            </p>

                            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #718096;">
                                Se você não solicitou este cadastro no Artfolio, pode ignorar esta mensagem com segurança.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 35px; background-color: #11131c; border-top: 1px solid rgba(255, 255, 255, 0.04); text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #718096;">
                                &copy; Artfolio Platform &bull; Conectando Artistas e Oportunidades
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def enviar_email_otp(destinatario_email: str, destinatario_nome: str, codigo_otp: str) -> bool:
    """
    Envia o e-mail transacional com o código OTP de 6 dígitos via API v3 do Brevo (Sendinblue).
    
    Lê a chave BREVO_API_KEY e o remetente BREVO_SENDER_EMAIL do settings/.env.
    Retorna True se a requisição foi aceita pela API do Brevo com sucesso, ou False em caso de falha.
    """
    api_key = settings.BREVO_API_KEY or os.getenv("BREVO_API_KEY", "")
    sender_email = settings.BREVO_SENDER_EMAIL or os.getenv("BREVO_SENDER_EMAIL", "noreply@artfolio.com")
    sender_name = settings.BREVO_SENDER_NAME or os.getenv("BREVO_SENDER_NAME", "Artfolio")

    if not api_key or not api_key.strip():
        logger.warning(
            f"[Brevo] BREVO_API_KEY não configurada no servidor. Código OTP gerado para {destinatario_email}: {codigo_otp}"
        )
        return False

    headers = {
        "accept": "application/json",
        "api-key": api_key.strip(),
        "content-type": "application/json"
    }

    html_content = construir_template_email_otp(destinatario_nome, codigo_otp)

    payload = {
        "sender": {
            "name": sender_name.strip(),
            "email": sender_email.strip()
        },
        "to": [
            {
                "email": destinatario_email.strip(),
                "name": destinatario_nome.strip() if destinatario_nome else destinatario_email.strip()
            }
        ],
        "subject": f"Seu código de verificação Artfolio: {codigo_otp}",
        "htmlContent": html_content
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code in (200, 201, 202):
            logger.info(
                f"[Brevo] E-mail OTP enviado com sucesso para {destinatario_email}. "
                f"Status: {response.status_code}, Resposta: {response.text}"
            )
            return True
        else:
            logger.error(
                f"[Brevo] Falha ao enviar e-mail OTP para {destinatario_email}. "
                f"Status: {response.status_code}, Erro: {response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"[Brevo] Exceção de rede ao contactar a API do Brevo: {e}")
        return False
