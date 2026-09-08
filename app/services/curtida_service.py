import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.curtida_model import Curtida
from app.repositories.curtida_repository import CurtidaRepository
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.notificacao_service import NotificacaoService
from app.redis_client import redis_client


class CurtidaService:
    """
    Serviço contendo as regras de negócio para curtidas (likes).
    Garante invalidação do cache de obras no Redis e envio de notificações em tempo real.
    """

    @staticmethod
    def curtir(db: Session, usuario_id: int, postagem_id: int) -> Curtida:
        """
        Registra a curtida de um usuário em uma postagem e emite evento WebSocket com métricas agregadas.
        """
        # 1. Verificar se a postagem existe e está ativa
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        # 2. Verificar se o usuário já curtiu
        curtida_existente = CurtidaRepository.buscar(db, usuario_id, postagem_id)
        if curtida_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você já curtiu esta postagem."
            )

        # 3. Criar a curtida
        nova_curtida = Curtida(
            idUsuario=usuario_id,
            idPostagem=postagem_id
        )
        curtida_salva = CurtidaRepository.criar(db, nova_curtida)

        # 4. Invalidar o cache do Feed no Redis
        redis_client.delete_pattern("artfolio:obras:*")

        # 5. Calcular total atualizado de curtidas
        total_curtidas = CurtidaRepository.contar_por_postagem(db, postagem_id)

        # 6. Disparar notificação automática e evento WebSocket ao autor da obra
        remetente = UsuarioRepository.buscar_por_id(db, usuario_id)
        nome_remetente = remetente.nome if remetente else "Alguém"
        foto_remetente = getattr(remetente, "fotoPerfil", None) if remetente else None

        notificacao = NotificacaoService.criar_notificacao(
            db=db,
            id_usuario=postagem.idUsuario,
            tipo="LIKE",
            titulo="Nova curtida",
            mensagem=f"{nome_remetente} curtiu sua publicação.",
            id_remetente=usuario_id,
            id_postagem=postagem_id,
            publicar_ws=False
        )

        payload_ws = {
            "id": notificacao.id if notificacao else None,
            "tipo": "CURTIDA",
            "postagem_id": postagem_id,
            "idPostagem": postagem_id,
            "total_curtidas": total_curtidas,
            "mensagem": f"{nome_remetente} curtiu sua publicação.",
            "remetente": {
                "id": remetente.id if remetente else usuario_id,
                "nome": nome_remetente,
                "fotoPerfil": foto_remetente
            },
            "naoLidasCount": NotificacaoService.contar_nao_lidas(db, postagem.idUsuario)
        }
        try:
            redis_client.publish(f"notificacoes:{postagem.idUsuario}", json.dumps(payload_ws, ensure_ascii=False))
        except Exception:
            pass

        return curtida_salva

    @staticmethod
    def descurtir(db: Session, usuario_id: int, postagem_id: int) -> dict:
        """
        Remove a curtida de um usuário em uma postagem, invalida o cache do Feed
        e emite evento WebSocket com a nova contagem para o autor da obra.
        """
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)

        curtida = CurtidaRepository.buscar(db, usuario_id, postagem_id)
        if not curtida:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curtida não encontrada."
            )

        CurtidaRepository.deletar(db, curtida)

        # Invalidar o cache do Feed no Redis
        redis_client.delete_pattern("artfolio:obras:*")

        total_curtidas = CurtidaRepository.contar_por_postagem(db, postagem_id)

        if postagem:
            payload_ws = {
                "tipo": "CURTIDA",
                "postagem_id": postagem_id,
                "idPostagem": postagem_id,
                "total_curtidas": total_curtidas,
                "curtido": False
            }
            try:
                redis_client.publish(f"notificacoes:{postagem.idUsuario}", json.dumps(payload_ws, ensure_ascii=False))
            except Exception:
                pass

        return {"message": "Curtida removida com sucesso.", "total_curtidas": total_curtidas}