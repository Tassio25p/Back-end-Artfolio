from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.notificacao_model import Notificacao
from app.repositories.notificacao_repository import NotificacaoRepository
from app.redis_client import redis_client


class NotificacaoService:
    """
    Serviço contendo as regras de negócio para as Notificações.

    Controla a criação automática de notificações, contagem de não lidas com
    suporte a cache Redis (fallback seguro), marcação de leitura e exclusão (soft delete).
    """

    @staticmethod
    def criar_notificacao(
        db: Session,
        id_usuario: int,
        tipo: str,
        titulo: str,
        mensagem: str,
        id_remetente: Optional[int] = None,
        id_postagem: Optional[int] = None,
        id_comentario: Optional[int] = None,
        id_conversa: Optional[int] = None
    ) -> Optional[Notificacao]:
        """
        Cria uma nova notificação no banco de dados.

        Regra: Não cria notificação se o remetente for a própria pessoa (ex: curtir/comentar própria obra).

        Args:
            db: Sessão ativa do SQLAlchemy.
            id_usuario: ID do destinatário da notificação.
            tipo: Tipo da notificação ('LIKE', 'FOLLOW', 'COMMENT', 'MESSAGE').
            titulo: Título da notificação.
            mensagem: Conteúdo da mensagem da notificação.
            id_remetente: ID do usuário que gerou a ação (opcional).
            id_postagem: ID da postagem relacionada (opcional).
            id_comentario: ID do comentário relacionado (opcional).
            id_conversa: ID da conversa relacionada (opcional).

        Returns:
            O objeto Notificacao criado, ou None se for uma auto-ação.
        """
        # 1. Não notificar se a ação for do próprio usuário sobre si mesmo
        if id_remetente and id_remetente == id_usuario:
            return None

        # 2. Criar e salvar o objeto
        nova_notificacao = Notificacao(
            idUsuario=id_usuario,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            idRemetente=id_remetente,
            idPostagem=id_postagem,
            idComentario=id_comentario,
            idConversa=id_conversa
        )
        notificacao_salva = NotificacaoRepository.criar(db, nova_notificacao)

        # 3. Invalidar cache de não lidas no Redis para o destinatário
        cache_key = f"notificacoes:nao_lidas:{id_usuario}"
        redis_client.delete(cache_key)

        return notificacao_salva

    @staticmethod
    def listar_notificacoes(db: Session, usuario_id: int) -> List[Notificacao]:
        """
        Retorna todas as notificações ativas do usuário autenticado (mais recentes primeiro).
        """
        return NotificacaoRepository.listar_por_usuario(db, usuario_id)

    @staticmethod
    def contar_nao_lidas(db: Session, usuario_id: int) -> int:
        """
        Retorna a quantidade de notificações não lidas.
        Utiliza cache Redis quando disponível, com fallback automático para o PostgreSQL.
        """
        cache_key = f"notificacoes:nao_lidas:{usuario_id}"
        
        # Tenta buscar do cache Redis
        val_cache = redis_client.get(cache_key)
        if val_cache is not None:
            try:
                return int(val_cache)
            except ValueError:
                pass

        # Busca do banco de dados se não estiver no cache
        qtd = NotificacaoRepository.contar_nao_lidas(db, usuario_id)

        # Salva no cache Redis por 5 minutos (300s)
        redis_client.set(cache_key, str(qtd), expira_segundos=300)

        return qtd

    @staticmethod
    def marcar_como_lida(db: Session, usuario_id: int, notificacao_id: int) -> Notificacao:
        """
        Marca uma notificação específica do usuário autenticado como lida.

        Raises:
            HTTPException 404: Se a notificação não existir.
            HTTPException 403: Se a notificação pertencer a outro usuário.
        """
        notificacao = NotificacaoRepository.buscar_por_id(db, notificacao_id)
        if not notificacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificação não encontrada."
            )

        if notificacao.idUsuario != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta notificação."
            )

        notificacao_atualizada = NotificacaoRepository.marcar_como_lida(db, notificacao)

        # Invalidar cache
        redis_client.delete(f"notificacoes:nao_lidas:{usuario_id}")

        return notificacao_atualizada

    @staticmethod
    def marcar_todas_como_lidas(db: Session, usuario_id: int) -> dict:
        """
        Marca todas as notificações não lidas do usuário autenticado como lidas.
        """
        qtd = NotificacaoRepository.marcar_todas_como_lidas(db, usuario_id)

        # Invalidar cache
        redis_client.delete(f"notificacoes:nao_lidas:{usuario_id}")

        return {
            "message": "Todas as notificações foram marcadas como lidas.",
            "atualizadas": qtd
        }

    @staticmethod
    def deletar_notificacao(db: Session, usuario_id: int, notificacao_id: int) -> dict:
        """
        Realiza o soft delete de uma notificação do usuário autenticado.

        Raises:
            HTTPException 404: Se a notificação não existir.
            HTTPException 403: Se a notificação pertencer a outro usuário.
        """
        notificacao = NotificacaoRepository.buscar_por_id(db, notificacao_id)
        if not notificacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificação não encontrada."
            )

        if notificacao.idUsuario != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para excluir esta notificação."
            )

        NotificacaoRepository.deletar(db, notificacao)

        # Invalidar cache
        redis_client.delete(f"notificacoes:nao_lidas:{usuario_id}")

        return {"message": "Notificação excluída com sucesso."}
