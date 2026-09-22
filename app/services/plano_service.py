from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.plano_model import Plano
from app.models.assinatura_model import Assinatura
from app.models.usuario_model import Usuario
from app.schemas.plano_schema import PlanoResposta, AssinaturaResposta, MeuPlanoResposta

class PlanoService:
    """
    Serviço responsável por regras de planos, assinaturas e permissões por plano no Artfolio.
    """

    @staticmethod
    def listar_planos(db: Session) -> List[PlanoResposta]:
        planos = db.query(Plano).filter(Plano.deletado == False, Plano.isAtivo == True).order_by(Plano.id).all()
        return [PlanoResposta.model_validate(p) for p in planos]

    @staticmethod
    def obter_tipo_plano_usuario(db: Session, usuario_id: int) -> str:
        """
        Retorna a string do tipo do plano ativo ('Free', 'Pro' ou 'Boost').
        """
        assinatura_ativa = (
            db.query(Assinatura)
            .join(Plano, Assinatura.idPlano == Plano.id)
            .filter(
                Assinatura.idUsuario == usuario_id,
                Assinatura.ativa == True,
                Assinatura.deletado == False,
                Plano.deletado == False
            )
            .first()
        )

        if not assinatura_ativa or not assinatura_ativa.plano:
            return "Free"

        tipo = assinatura_ativa.plano.tipo.strip().lower()
        if "boost" in tipo:
            return "Boost"
        if "pro" in tipo:
            return "Pro"
        return "Free"

    @staticmethod
    def obter_meu_plano(db: Session, usuario: Usuario) -> MeuPlanoResposta:
        assinatura_ativa = (
            db.query(Assinatura)
            .join(Plano, Assinatura.idPlano == Plano.id)
            .filter(
                Assinatura.idUsuario == usuario.id,
                Assinatura.ativa == True,
                Assinatura.deletado == False,
                Plano.deletado == False
            )
            .order_by(Assinatura.id.desc())
            .first()
        )

        agora = datetime.now(timezone.utc)
        if assinatura_ativa and assinatura_ativa.dataFim and assinatura_ativa.dataFim < agora:
            assinatura_ativa.ativa = False
            db.commit()
            assinatura_ativa = None

        # Definir valores padrão para o plano Free
        tipo_plano: str = "Free"
        nome_exibicao: str = "Artfolio Free"
        cor: str = "artGreen"
        preco: float = 0.00
        limite_arquivos: int = 1
        limite_mb: int = 10
        permite_carrossel: bool = False
        permite_analytics: bool = False
        permite_mensagem_cta: bool = False
        permite_destaque: bool = False
        assinatura_schema: Optional[AssinaturaResposta] = None

        # Verificar se o usuário possui assinatura ativa válida com plano associado
        if assinatura_ativa and assinatura_ativa.plano:
            p = assinatura_ativa.plano
            tipo_bruto = str(p.tipo or "").strip().lower()
            if "boost" in tipo_bruto:
                tipo_plano = "Boost"
                nome_exibicao = "Artfolio Boost"
                cor = "artOrange"
                preco = float(getattr(p, "precoPlano", 0.0) or 0.0)
                limite_arquivos = 10
                limite_mb = 100
                permite_carrossel = True
                permite_analytics = True
                permite_mensagem_cta = True
                permite_destaque = False
            elif "pro" in tipo_bruto:
                tipo_plano = "Pro"
                nome_exibicao = "Artfolio Pro"
                cor = "artPurple"
                preco = float(getattr(p, "precoPlano", 0.0) or 0.0)
                limite_arquivos = 10
                limite_mb = 50
                permite_carrossel = True
                permite_analytics = True
                permite_mensagem_cta = False
                permite_destaque = False
            else:
                tipo_plano = "Free"

            # Validar o schema de assinatura apenas quando ela existe
            try:
                assinatura_schema = AssinaturaResposta.model_validate(assinatura_ativa)
            except Exception:
                assinatura_schema = None
        else:
            assinatura_schema = None

        msg_cta = getattr(usuario, "mensagem_cta", None)
        raw_led = getattr(usuario, "mostrar_moldura_led", True)
        mostrar_led = True if raw_led is None else bool(raw_led)

        return MeuPlanoResposta(
            tipo=str(tipo_plano),
            nomeExibicao=str(nome_exibicao),
            cor=str(cor),
            precoPlano=float(preco),
            mostrar_moldura_led=mostrar_led,
            mensagem_cta=str(msg_cta) if msg_cta else None,
            limiteArquivosPorPost=int(limite_arquivos),
            limite_mb=int(limite_mb),
            permiteCarrossel=bool(permite_carrossel),
            permiteAnalytics=bool(permite_analytics),
            permiteMensagemCta=bool(permite_mensagem_cta),
            permiteDestaqueFeed=bool(permite_destaque),
            assinatura=assinatura_schema
        )

    @staticmethod
    def _resetar_customizacoes_downgrade(db: Session, usuario: Usuario) -> None:
        """
        Ao retornar ou fazer downgrade para o plano Free, reseta as personalizações visuais
        exclusivas (cor de LED para o padrão, limpa cor de nick, imagem de fundo, mensagem CTA
        e avatar em GIF) preservando intactas as postagens já criadas no banco de dados.
        """
        if not usuario:
            return

        usuario.cor_led_hex = None
        usuario.mensagem_cta = None

        if usuario.fotoPerfil and ".gif" in usuario.fotoPerfil.lower():
            usuario.fotoPerfil = None

        db.commit()

        try:
            from app.redis_client import redis_client
            redis_client.delete(f"artfolio:perfil:{usuario.id}")
            redis_client.delete_pattern("artfolio:obras:*")
        except Exception:
            pass

    @staticmethod
    def assinar_plano(db: Session, usuario: Usuario, plano_id: int) -> MeuPlanoResposta:
        plano = db.query(Plano).filter(Plano.id == plano_id, Plano.deletado == False).first()
        if not plano:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano não encontrado."
            )

        # Se escolher Free, desativa assinaturas pagas anteriores e reseta personalizações exclusivas
        if plano.tipo.strip().lower() == "free":
            db.query(Assinatura).filter(
                Assinatura.idUsuario == usuario.id,
                Assinatura.ativa == True
            ).update({"ativa": False})
            db.commit()

            PlanoService._resetar_customizacoes_downgrade(db, usuario)
            return PlanoService.obter_meu_plano(db, usuario)

        # Se escolher Pro, desativa assinaturas anteriores e limpa customizações exclusivas de Boost
        if plano.tipo.strip().lower() == "pro":
            usuario.mensagem_cta = None
            if usuario.fotoPerfil and ".gif" in usuario.fotoPerfil.lower():
                usuario.fotoPerfil = None
            db.commit()
            try:
                from app.redis_client import redis_client
                redis_client.delete(f"artfolio:perfil:{usuario.id}")
                redis_client.delete_pattern("artfolio:obras:*")
            except Exception:
                pass

        # Desativar quaisquer assinaturas ativas anteriores para garantir unicidade
        db.query(Assinatura).filter(
            Assinatura.idUsuario == usuario.id,
            Assinatura.ativa == True
        ).update({"ativa": False})

        # Criar nova assinatura ativa
        agora = datetime.now(timezone.utc)
        fim = agora + timedelta(days=30)
        nova_assinatura = Assinatura(
            idUsuario=usuario.id,
            idPlano=plano.id,
            dataInicio=agora,
            dataFim=fim,
            ativa=True,
            deletado=False
        )
        db.add(nova_assinatura)
        db.commit()
        db.refresh(nova_assinatura)

        return PlanoService.obter_meu_plano(db, usuario)

    @staticmethod
    def ativar_assinatura_stripe(
        db: Session,
        usuario_id: int,
        plano_id: Optional[int] = None,
        tipo_plano: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None
    ) -> Assinatura:
        """
        Ativa ou renova a assinatura de um usuário após a confirmação do pagamento pelo Stripe.
        Desativa assinaturas ativas anteriores, persiste a nova vigência de 30 dias e emite notificação no sistema.
        """
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.deletado == False).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário ID {usuario_id} não encontrado para ativação de assinatura."
            )

        plano = None
        if plano_id:
            try:
                p_id_int = int(plano_id)
                plano = db.query(Plano).filter(Plano.id == p_id_int, Plano.deletado == False).first()
            except (ValueError, TypeError):
                pass

        if not plano and tipo_plano:
            plano = db.query(Plano).filter(
                Plano.tipo.ilike(f"%{tipo_plano.strip()}%"),
                Plano.deletado == False
            ).first()

        if not plano:
            # Fallback seguro para Pro se não especificado
            plano = db.query(Plano).filter(Plano.tipo.ilike("%pro%"), Plano.deletado == False).first()

        if not plano:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano solicitado não foi encontrado no banco de dados."
            )

        # Se for Pro, limpa customizações exclusivas do plano Boost
        if plano.tipo.strip().lower() == "pro":
            usuario.mensagem_cta = None
            if usuario.fotoPerfil and ".gif" in usuario.fotoPerfil.lower():
                usuario.fotoPerfil = None
            db.commit()

        # Desativar assinaturas ativas anteriores
        db.query(Assinatura).filter(
            Assinatura.idUsuario == usuario.id,
            Assinatura.ativa == True
        ).update({"ativa": False})

        # Criar nova assinatura com vigência de 30 dias
        agora = datetime.now(timezone.utc)
        fim = agora + timedelta(days=30)
        nova_assinatura = Assinatura(
            idUsuario=usuario.id,
            idPlano=plano.id,
            dataInicio=agora,
            dataFim=fim,
            ativa=True,
            deletado=False
        )
        db.add(nova_assinatura)
        db.commit()
        db.refresh(nova_assinatura)

        # Atualizar atributo plano do usuário e invalidar cache Redis
        usuario.plano = plano.tipo
        try:
            from app.redis_client import redis_client
            redis_client.delete(f"artfolio:perfil:{usuario.id}")
            redis_client.delete_pattern("artfolio:obras:*")
        except Exception:
            pass

        # Disparar notificação interna no sistema
        try:
            from app.models.notificacao_model import Notificacao
            notif = Notificacao(
                idUsuario=usuario.id,
                tipo="sistema",
                titulo="Assinatura Confirmada!",
                mensagem=f"Seu pagamento foi confirmado com sucesso! O plano Artfolio {plano.tipo} já está ativo na sua conta.",
                lida=False,
                link_acao="/planos"
            )
            db.add(notif)
            db.commit()
        except Exception:
            pass

        return nova_assinatura
