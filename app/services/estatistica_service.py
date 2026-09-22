from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.postagem_model import Postagem
from app.models.postagem_categoria_model import PostagemCategoria
from app.models.categoria_model import Categoria
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.obra_salva_model import ObraSalva
from app.models.seguidor_model import Seguidor
from app.services.plano_service import PlanoService

class EstatisticaService:
    """
    Serviço que consolida as estatísticas e métricas analíticas de portfólio dos artistas.
    """

    @staticmethod
    def obter_painel_artista(db: Session, artista_id: int) -> Dict[str, Any]:
        tipo_plano = PlanoService.obter_tipo_plano_usuario(db, artista_id)
        is_pro_ou_boost = tipo_plano in ("Pro", "Boost")

        # Contagem real de obras ativas (sempre liberado e nítido)
        total_obras = db.query(func.count(Postagem.id)).filter(
            Postagem.idUsuario == artista_id,
            Postagem.deletado == False
        ).scalar() or 0

        # Bloqueio de segurança no backend: usuários Free não recebem métricas do banco
        if not is_pro_ou_boost:
            return {
                "artistaId": artista_id,
                "tipoPlano": tipo_plano,
                "plano": tipo_plano,
                "disponivel": False,
                "acesso_permitido": False,
                "obras_ativas": total_obras,
                "mensagem": "Faça upgrade para Artfolio Pro ou Boost para desbloquear as métricas completas da sua conta.",
                "totais": {
                    "obras": total_obras,
                    "curtidas": 0,
                    "salvos": 0,
                    "comentarios": 0,
                    "visualizacoes": 0,
                    "seguidores": 0
                },
                "periodos": {
                    "seguidoresSemana": 0,
                    "seguidoresMes": 0
                },
                "podioCategorias": []
            }

        # Usuários Pro ou Boost: calcular métricas completas
        obras = db.query(Postagem).filter(
            Postagem.idUsuario == artista_id,
            Postagem.deletado == False
        ).all()
        obra_ids = [o.id for o in obras]

        # Se não tiver obras
        if not obra_ids:
            total_curtidas = 0
            total_comentarios = 0
            total_salvos = 0
            total_visualizacoes = 0
            podio_categorias = []
        else:
            # Total de curtidas
            total_curtidas = db.query(func.count(Curtida.idUsuario)).filter(
                Curtida.idPostagem.in_(obra_ids)
            ).scalar() or 0

            # Total de comentários
            total_comentarios = db.query(func.count(Comentario.id)).filter(
                Comentario.idPostagem.in_(obra_ids),
                Comentario.deletado == False
            ).scalar() or 0

            # Total de obras salvas
            total_salvos = db.query(func.count(ObraSalva.id)).filter(
                ObraSalva.idPostagem.in_(obra_ids)
            ).scalar() or 0

            # Total de visualizações
            total_visualizacoes = sum(o.visualizacoes or 0 for o in obras)

            # Pódio de categorias: agrupar por categoria e somar engajamento
            categorias_engajamento: Dict[str, Dict[str, Any]] = {}
            for o in obras:
                engajamento_obra = (o.visualizacoes or 0)
                curtidas_obra = db.query(func.count(Curtida.idUsuario)).filter(
                    Curtida.idPostagem == o.id
                ).scalar() or 0
                comentarios_obra = db.query(func.count(Comentario.id)).filter(
                    Comentario.idPostagem == o.id, Comentario.deletado == False
                ).scalar() or 0
                pontos = engajamento_obra + (curtidas_obra * 3) + (comentarios_obra * 2)

                for cat in o.categorias:
                    nome_cat = cat.nomeCategoria
                    if nome_cat not in categorias_engajamento:
                        categorias_engajamento[nome_cat] = {
                            "categoria": nome_cat,
                            "obras": 0,
                            "curtidas": 0,
                            "visualizacoes": 0,
                            "pontos": 0
                        }
                    categorias_engajamento[nome_cat]["obras"] += 1
                    categorias_engajamento[nome_cat]["curtidas"] += curtidas_obra
                    categorias_engajamento[nome_cat]["visualizacoes"] += (o.visualizacoes or 0)
                    categorias_engajamento[nome_cat]["pontos"] += pontos

            # Ordenar pelo engajamento e pegar top 3 (ouro, prata, bronze)
            ranking = sorted(categorias_engajamento.values(), key=lambda x: x["pontos"], reverse=True)
            podio_categorias = ranking[:3]

        # 2. Seguidores: Total, Novos na Semana, Novos no Mês
        total_seguidores = db.query(func.count(Seguidor.idSeguidor)).filter(
            Seguidor.idSeguido == artista_id
        ).scalar() or 0

        agora = datetime.now(timezone.utc)
        uma_semana_atras = agora - timedelta(days=7)
        um_mes_atras = agora - timedelta(days=30)

        seguidores_semana = db.query(func.count(Seguidor.idSeguidor)).filter(
            Seguidor.idSeguido == artista_id,
            Seguidor.dataSeguiu >= uma_semana_atras
        ).scalar() or 0

        seguidores_mes = db.query(func.count(Seguidor.idSeguidor)).filter(
            Seguidor.idSeguido == artista_id,
            Seguidor.dataSeguiu >= um_mes_atras
        ).scalar() or 0

        return {
            "artistaId": artista_id,
            "tipoPlano": tipo_plano,
            "plano": tipo_plano,
            "disponivel": True,
            "acesso_permitido": True,
            "obras_ativas": len(obra_ids),
            "mensagem": "Painel liberado",
            "totais": {
                "curtidas": total_curtidas,
                "salvos": total_salvos,
                "comentarios": total_comentarios,
                "visualizacoes": total_visualizacoes,
                "obras": len(obra_ids),
                "seguidores": total_seguidores
            },
            "periodos": {
                "seguidoresSemana": seguidores_semana,
                "seguidoresMes": seguidores_mes
            },
            "podioCategorias": podio_categorias
        }
