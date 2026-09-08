from typing import List, Optional
from datetime import datetime, timedelta
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
        return [
            PlanoResposta(
                id=p.id,
                tipo=p.tipo,
                precoPlano=float(p.precoPlano) if p.precoPlano is not None else 0.0,
                descricao=p.descricao,
                isAtivo=p.isAtivo
            )
            for p in planos
        ]

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

        agora = datetime.utcnow()
        if assinatura_ativa and assinatura_ativa.dataFim and assinatura_ativa.dataFim < agora:
            assinatura_ativa.ativa = False
            db.commit()
            assinatura_ativa = None

        tipo_plano = "Free"
        preco = 0.00
        assinatura_schema = None

        if assinatura_ativa and assinatura_ativa.plano:
            p = assinatura_ativa.plano
            tipo_bruto = p.tipo.strip().lower()
            if "boost" in tipo_bruto:
                tipo_plano = "Boost"
            elif "pro" in tipo_bruto:
                tipo_plano = "Pro"
            else:
                tipo_plano = "Free"

            preco = float(p.precoPlano) if p.precoPlano is not None else 0.00
            assinatura_schema = AssinaturaResposta(
                id=assinatura_ativa.id,
                idUsuario=assinatura_ativa.idUsuario,
                idPlano=assinatura_ativa.idPlano,
                dataInicio=assinatura_ativa.dataInicio,
                dataFim=assinatura_ativa.dataFim,
                ativa=assinatura_ativa.ativa,
                plano=PlanoResposta(
                    id=p.id,
                    tipo=p.tipo,
                    precoPlano=preco,
                    descricao=p.descricao,
                    isAtivo=p.isAtivo
                )
            )

        if tipo_plano == "Boost":
            nome_exibicao = "Artfolio Boost"
            cor = "artOrange"
            limite_arquivos = 10
            permite_carrossel = True
            permite_analytics = True
            permite_destaque = True
        elif tipo_plano == "Pro":
            nome_exibicao = "Artfolio Pro"
            cor = "artPurple"
            limite_arquivos = 10
            permite_carrossel = True
            permite_analytics = True
            permite_destaque = False
        else:
            nome_exibicao = "Artfolio Free"
            cor = "artGreen"
            limite_arquivos = 1
            permite_carrossel = False
            permite_analytics = False
            permite_destaque = False

        return MeuPlanoResposta(
            tipo=tipo_plano,
            nomeExibicao=nome_exibicao,
            cor=cor,
            precoPlano=preco,
            mostrar_moldura_led=getattr(usuario, "mostrar_moldura_led", True),
            mensagem_cta=getattr(usuario, "mensagem_cta", None),
            limiteArquivosPorPost=limite_arquivos,
            permiteCarrossel=permite_carrossel,
            permiteAnalytics=permite_analytics,
            permiteDestaqueFeed=permite_destaque,
            assinatura=assinatura_schema
        )

    @staticmethod
    def assinar_plano(db: Session, usuario: Usuario, plano_id: int) -> MeuPlanoResposta:
        plano = db.query(Plano).filter(Plano.id == plano_id, Plano.deletado == False).first()
        if not plano:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano não encontrado."
            )

        # Se escolher Free, pode simplesmente desativar assinaturas pagas anteriores
        if plano.tipo.strip().lower() == "free":
            db.query(Assinatura).filter(
                Assinatura.idUsuario == usuario.id,
                Assinatura.ativa == True
            ).update({"ativa": False})
            db.commit()
            return PlanoService.obter_meu_plano(db, usuario)

        # Desativar quaisquer assinaturas ativas anteriores para garantir unicidade
        db.query(Assinatura).filter(
            Assinatura.idUsuario == usuario.id,
            Assinatura.ativa == True
        ).update({"ativa": False})

        # Criar nova assinatura ativa
        agora = datetime.utcnow()
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
