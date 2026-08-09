from typing import List
from sqlalchemy.orm import Session
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.curtida_repository import CurtidaRepository
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.seguidor_repository import SeguidorRepository
from app.schemas.postagem_schema import FeedItemResposta, FeedUsuarioResposta, CategoriaResposta


class FeedService:
    """
    Serviço responsável por montar o feed de postagens.

    Busca as postagens ativas ordenadas por data (mais recentes primeiro)
    e enriquece cada item com contagens de likes, comentários, seguidores
    e flags de interação do usuário autenticado.
    """

    @staticmethod
    def obter_feed(db: Session, usuario_id: int) -> List[FeedItemResposta]:
        """
        Monta o feed cronológico para o usuário autenticado.

        Para cada postagem ativa, calcula:
        - Quantidade de likes
        - Quantidade de comentários
        - Quantidade de seguidores do autor
        - Se o usuário autenticado curtiu a postagem
        - Se o usuário autenticado segue o autor

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (do JWT).

        Returns:
            Lista de FeedItemResposta ordenada por dataPostagem DESC.
        """
        # 1. Buscar todas as postagens ativas, mais recentes primeiro
        postagens = PostagemRepository.listar_todas(db)

        # 2. Montar o feed enriquecido
        feed_items = []
        for postagem in postagens:
            # Contagens
            total_likes = CurtidaRepository.contar_por_postagem(db, postagem.id)
            total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem.id)
            total_seguidores = SeguidorRepository.contar_seguidores(db, postagem.idUsuario)

            # Flags de interação do usuário autenticado
            curtido = CurtidaRepository.buscar(db, usuario_id, postagem.id) is not None
            seguindo = SeguidorRepository.buscar(db, usuario_id, postagem.idUsuario) is not None

            # Montar o schema do usuário autor
            usuario_resp = None
            if postagem.usuario:
                usuario_resp = FeedUsuarioResposta(
                    id=postagem.usuario.id,
                    nome=postagem.usuario.nome,
                    fotoPerfil=postagem.usuario.fotoPerfil,
                    tipo_conta=postagem.usuario.tipo_conta,
                )

            # Montar o schema da categoria
            categoria_resp = None
            if postagem.categoria:
                categoria_resp = CategoriaResposta(
                    id=postagem.categoria.id,
                    nomeCategoria=postagem.categoria.nomeCategoria,
                )

            # Montar o item do feed
            item = FeedItemResposta(
                id=postagem.id,
                legenda=postagem.legenda,
                arquivoUrl=postagem.arquivoUrl,
                dataPostagem=postagem.dataPostagem,
                usuario=usuario_resp,
                categoria=categoria_resp,
                likes=total_likes,
                comentarios=total_comentarios,
                seguidores=total_seguidores,
                curtido_por_mim=curtido,
                seguindo_usuario=seguindo,
            )
            feed_items.append(item)

        return feed_items
