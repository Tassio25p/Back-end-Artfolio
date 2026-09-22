from typing import List, Optional, Set
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
    carrossel de imagens e identidade visual do autor.
    O feed é 100% orgânico e meritocrático, sem manipulação de visibilidade por planos pagos.
    """

    @staticmethod
    def obter_feed(db: Session, usuario_id: Optional[int] = None) -> List[FeedItemResposta]:
        """
        Monta o feed cronológico e orgânico para o usuário autenticado ou visitante anônimo.
        """
        # 1. Buscar todas as postagens ativas
        postagens = PostagemRepository.listar_todas(db)

        # Cache local por artista para evitar queries repetidas
        planos_cache = {}

        feed_items = []
        for postagem in postagens:
            # Contagens
            total_likes = CurtidaRepository.contar_por_postagem(db, postagem.id)
            total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem.id)
            total_seguidores = SeguidorRepository.contar_seguidores(db, postagem.idUsuario)

            # Flags de interação do usuário autenticado (False caso anônimo)
            curtido = CurtidaRepository.buscar(db, usuario_id, postagem.id) is not None if usuario_id else False
            seguindo = SeguidorRepository.buscar(db, usuario_id, postagem.idUsuario) is not None if usuario_id else False
            salvo = ObraSalvaRepository.buscar(db, usuario_id, postagem.id) is not None if usuario_id else False

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

            # Montar o item do feed puramente orgânico
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
                destaque_boost=False,
            )
            feed_items.append(item)

        return feed_items
