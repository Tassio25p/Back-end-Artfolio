import json
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.comentario_model import Comentario
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.comentario_schema import ComentarioCriar
from app.services.notificacao_service import NotificacaoService
from app.redis_client import redis_client


class ComentarioService:
    """
    Serviço contendo as regras de negócio para comentários.
    Invalida o cache do feed no Redis e emite eventos WebSocket em tempo real.
    """

    @staticmethod
    def criar_comentario(
        db: Session,
        usuario_id: int,
        postagem_id: int,
        dados: ComentarioCriar
    ) -> Comentario:
        """
        Cria um novo comentário em uma postagem e emite evento WebSocket com contagem atualizada.
        """
        # 1. Verificar se a postagem existe e está ativa
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        # 2. Criar o comentário
        novo_comentario = Comentario(
            idUsuario=usuario_id,
            idPostagem=postagem_id,
            conteudo=dados.conteudo
        )
        comentario_salvo = ComentarioRepository.criar(db, novo_comentario)

        # 3. Invalidar o cache do Feed no Redis
        redis_client.delete_pattern("artfolio:obras:*")

        # 4. Calcular total atualizado de comentários
        total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem_id)

        # 5. Disparar notificação automática e evento WebSocket ao autor da obra
        remetente = UsuarioRepository.buscar_por_id(db, usuario_id)
        nome_remetente = remetente.nome if remetente else "Alguém"
        foto_remetente = getattr(remetente, "fotoPerfil", None) if remetente else None

        notificacao = NotificacaoService.criar_notificacao(
            db=db,
            id_usuario=postagem.idUsuario,
            tipo="COMMENT",
            titulo="Novo comentário",
            mensagem=f"{nome_remetente} comentou na sua publicação.",
            id_remetente=usuario_id,
            id_postagem=postagem_id,
            id_comentario=comentario_salvo.id,
            publicar_ws=False
        )

        payload_ws = {
            "id": notificacao.id if notificacao else None,
            "tipo": "COMENTARIO",
            "postagem_id": postagem_id,
            "idPostagem": postagem_id,
            "total_comentarios": total_comentarios,
            "mensagem": f"{nome_remetente} comentou na sua publicação.",
            "remetente": {
                "id": remetente.id if remetente else usuario_id,
                "nome": nome_remetente,
                "fotoPerfil": foto_remetente
            },
            "naoLidasCount": NotificacaoService.contar_nao_lidas(db, postagem.idUsuario)
        }
        publicado = False
        try:
            publicado = bool(redis_client.publish(f"notificacoes:{postagem.idUsuario}", json.dumps(payload_ws, ensure_ascii=False)))
        except Exception:
            publicado = False
        if not publicado:
            try:
                from app.core.websocket_manager import manager
                manager.dispatch_personal_message_sync(postagem.idUsuario, payload_ws)
            except Exception:
                pass

        if comentario_salvo.usuario:
            from app.services.plano_service import PlanoService
            comentario_salvo.usuario.plano = PlanoService.obter_tipo_plano_usuario(db, comentario_salvo.usuario.id)

        return comentario_salvo

    @staticmethod
    def listar_comentarios(db: Session, postagem_id: int) -> List[Comentario]:
        """
        Lista todos os comentários ativos de uma postagem.
        """
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        from app.services.plano_service import PlanoService
        comentarios = ComentarioRepository.listar_por_postagem(db, postagem_id)
        for c in comentarios:
            if c.usuario:
                c.usuario.plano = PlanoService.obter_tipo_plano_usuario(db, c.usuario.id)
        return comentarios

    @staticmethod
    def deletar_comentario(
        db: Session,
        usuario_id: int,
        comentario_id: int,
        tipo_conta: str
    ) -> dict:
        """
        Exclui um comentário (soft delete) e invalida o cache do Feed.
        """
        # 1. Buscar o comentário
        comentario = ComentarioRepository.buscar_por_id(db, comentario_id)
        if not comentario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comentário não encontrado."
            )

        # 2. Verificar permissão: dono ou admin/moderador
        tipos_admin = ["admin", "moderador"]
        if comentario.idUsuario != usuario_id and tipo_conta not in tipos_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para excluir este comentário."
            )

        postagem_id = comentario.idPostagem
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)

        # 3. Soft delete
        ComentarioRepository.deletar(db, comentario)

        # 4. Invalidar o cache do Feed no Redis
        redis_client.delete_pattern("artfolio:obras:*")

        total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem_id)

        if postagem:
            payload_ws = {
                "tipo": "COMENTARIO",
                "postagem_id": postagem_id,
                "idPostagem": postagem_id,
                "total_comentarios": total_comentarios,
                "removido": True
            }
            publicado = False
            try:
                publicado = bool(redis_client.publish(f"notificacoes:{postagem.idUsuario}", json.dumps(payload_ws, ensure_ascii=False)))
            except Exception:
                publicado = False
            if not publicado:
                try:
                    from app.core.websocket_manager import manager
                    manager.dispatch_personal_message_sync(postagem.idUsuario, payload_ws)
                except Exception:
                    pass

        return {"message": "Comentário excluído com sucesso.", "total_comentarios": total_comentarios}
