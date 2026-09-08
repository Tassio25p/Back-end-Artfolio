from typing import List, Set
from sqlalchemy.orm import Session
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.curtida_repository import CurtidaRepository
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.seguidor_repository import SeguidorRepository
from app.repositories.obra_salva_repository import ObraSalvaRepository
from app.models.preferencia_usuario_model import PreferenciaUsuario
from app.schemas.postagem_schema import FeedItemResposta, FeedUsuarioResposta, CategoriaResposta
from app.services.plano_service import PlanoService


class FeedService:
    """
    Serviço responsável por montar o feed de postagens.

    Busca as postagens ativas ordenadas por data (mais recentes primeiro)
    e enriquece cada item com contagens de likes, comentários, seguidores,
    carrossel de imagens, identidade de plano e destaque segmentado para o plano Boost.
    """

    @staticmethod
    def obter_feed(db: Session, usuario_id: int) -> List[FeedItemResposta]:
        """
        Monta o feed cronológico para o usuário autenticado com priorização orgânica Boost.
        """
        # 1. Obter categorias de interesse do usuário atual
        preferencias = db.query(PreferenciaUsuario).filter(PreferenciaUsuario.idUsuario == usuario_id).all()
        ids_categorias_preferidas: Set[int] = {p.idCategoria for p in preferencias}

        # 2. Buscar todas as postagens ativas
        postagens = PostagemRepository.listar_todas(db)

        # Cache local por artista para evitar queries repetidas
        planos_cache = {}

        feed_items = []
        for postagem in postagens:
            # Contagens
            total_likes = CurtidaRepository.contar_por_postagem(db, postagem.id)
            total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem.id)
            total_seguidores = SeguidorRepository.contar_seguidores(db, postagem.idUsuario)

            # Flags de interação do usuário autenticado
            curtido = CurtidaRepository.buscar(db, usuario_id, postagem.id) is not None
            seguindo = SeguidorRepository.buscar(db, usuario_id, postagem.idUsuario) is not None
            salvo = ObraSalvaRepository.buscar(db, usuario_id, postagem.id) is not None

            # Obter plano do autor
            if postagem.idUsuario not in planos_cache:
                planos_cache[postagem.idUsuario] = PlanoService.obter_tipo_plano_usuario(db, postagem.idUsuario)
            plano_autor = planos_cache[postagem.idUsuario]

            # Montar o schema do usuário autor
            usuario_resp = None
            if postagem.usuario:
                usuario_resp = FeedUsuarioResposta(
                    id=postagem.usuario.id,
                    nome=postagem.usuario.nome,
                    fotoPerfil=postagem.usuario.fotoPerfil,
                    tipo_conta=postagem.usuario.tipo_conta,
                    plano=plano_autor,
                    mostrar_moldura_led=getattr(postagem.usuario, "mostrar_moldura_led", True)
                )

            # Montar o schema da categoria
            categoria_resp = None
            if postagem.categoria:
                categoria_resp = CategoriaResposta(
                    id=postagem.categoria.id,
                    nomeCategoria=postagem.categoria.nomeCategoria,
                )

            categorias_obra_ids = [cat.id for cat in postagem.categorias] if postagem.categorias else []
            if postagem.idCategoria and postagem.idCategoria not in categorias_obra_ids:
                categorias_obra_ids.append(postagem.idCategoria)

            # Destaque Boost Segmentado (Não-Seguidores que consomem a categoria)
            eh_boost = (plano_autor == "Boost")
            consome_categoria = bool(ids_categorias_preferidas.intersection(categorias_obra_ids))
            destaque_boost = eh_boost and (not seguindo) and consome_categoria

            # Montar o item do feed
            item = FeedItemResposta(
                id=postagem.id,
                legenda=postagem.legenda,
                arquivoUrl=postagem.arquivoUrl,
                arquivos=postagem.lista_arquivos,
                dataPostagem=postagem.dataPostagem,
                usuario=usuario_resp,
                categoria=categoria_resp,
                likes=total_likes,
                comentarios=total_comentarios,
                visualizacoes=postagem.visualizacoes or 0,
                seguidores=total_seguidores,
                curtido_por_mim=curtido,
                seguindo_usuario=seguindo,
                salvo_por_mim=salvo,
                destaque_boost=destaque_boost,
            )
            feed_items.append(item)

        # Priorização elegante: itens com destaque_boost sobem de forma justa e intercalada
        destaques = [it for it in feed_items if it.destaque_boost]
        organicos = [it for it in feed_items if not it.destaque_boost]

        # Intercalar 1 destaque a cada 3 itens orgânicos
        resultado_final = []
        d_idx = 0
        for i, org in enumerate(organicos):
            if i > 0 and i % 3 == 0 and d_idx < len(destaques):
                resultado_final.append(destaques[d_idx])
                d_idx += 1
            resultado_final.append(org)
        
        # Anexa restantes de destaques caso existam
        while d_idx < len(destaques):
            resultado_final.append(destaques[d_idx])
            d_idx += 1

        return resultado_final if resultado_final else feed_items
