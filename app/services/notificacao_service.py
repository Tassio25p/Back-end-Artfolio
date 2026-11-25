import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.notificacao_model import Notificacao
from app.repositories.notificacao_repository import NotificacaoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.redis_client import redis_client


class NotificacaoService:
    """
    Serviço contendo as regras de negócio para as Notificações.

    Controla a criação automática de notificações, contagem de não lidas com
    suporte a cache Redis (fallback seguro), marcação de leitura, exclusão (soft delete)
    e emissão de eventos em tempo real via Redis Pub/Sub e WebSockets.
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
        id_conversa: Optional[int] = None,
        publicar_ws: bool = True
    ) -> Optional[Notificacao]:
        """
        Cria uma nova notificação no banco de dados e transmite via Redis Pub/Sub.

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

        # 4. Obter informações do remetente para enriquecer a notificação em tempo real
        remetente_info = None
        if id_remetente:
            remetente = UsuarioRepository.buscar_por_id(db, id_remetente)
            if remetente:
                remetente_info = {
                    "id": remetente.id,
                    "nome": remetente.nome,
                    "fotoPerfil": remetente.fotoPerfil,
                    "foto_perfil": remetente.fotoPerfil,
                    "tipo_conta": getattr(remetente, "tipo_conta", "artista"),
                    "plano": getattr(remetente, "plano", "Free"),
                }

        total_nao_lidas = NotificacaoRepository.contar_nao_lidas(db, id_usuario)

        tipo_normalizado = tipo
        if tipo == "LIKE":
            tipo_normalizado = "CURTIDA"
        elif tipo == "COMMENT":
            tipo_normalizado = "COMENTARIO"
        elif tipo == "FOLLOW":
            tipo_normalizado = "SEGUIDOR"

        total_curtidas = None
        total_comentarios = None
        total_seguidores = None

        if id_postagem:
            from app.repositories.curtida_repository import CurtidaRepository
            from app.repositories.comentario_repository import ComentarioRepository
            total_curtidas = CurtidaRepository.contar_por_postagem(db, id_postagem)
            total_comentarios = ComentarioRepository.contar_por_postagem(db, id_postagem)

        if tipo_normalizado == "SEGUIDOR":
            from app.repositories.seguidor_repository import SeguidorRepository
            total_seguidores = SeguidorRepository.contar_seguidores(db, id_usuario)

        payload = {
            "id": notificacao_salva.id,
            "tipo": tipo_normalizado,
            "tipo_original": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "id_usuario": id_usuario,
            "seguido_id": id_usuario if tipo_normalizado == "SEGUIDOR" else None,
            "id_remetente": id_remetente,
            "id_postagem": id_postagem,
            "postagem_id": id_postagem,
            "id_comentario": id_comentario,
            "id_conversa": id_conversa,
            "remetente": remetente_info,
            "dataCriacao": notificacao_salva.dataCriacao.isoformat() if notificacao_salva.dataCriacao else None,
            "naoLidasCount": total_nao_lidas,
            "total_curtidas": total_curtidas,
            "total_comentarios": total_comentarios,
            "total_seguidores": total_seguidores,
        }

        # 5. Publicar evento no Redis Pub/Sub para entrega instantânea via WebSocket (se solicitado)
        if publicar_ws:
            canal = f"notificacoes:{id_usuario}"
            publicado = False
            try:
                publicado = bool(redis_client.publish(canal, json.dumps(payload, ensure_ascii=False)))
            except Exception:
                publicado = False
            if not publicado:
                try:
                    from app.core.websocket_manager import manager
                    manager.dispatch_personal_message_sync(id_usuario, payload)
                except Exception:
                    pass

        return notificacao_salva

    @staticmethod
    def serializar_notificacao(notificacao: Notificacao) -> dict:
        """
        Serializa o modelo Notificacao para um dicionário padronizado,
        garantindo os campos essenciais da Fase 3 e os campos legados para retrocompatibilidade.
        """
        rem = None
        if notificacao.remetente:
            rem = {
                "id": notificacao.remetente.id,
                "nome": notificacao.remetente.nome,
                "fotoPerfil": notificacao.remetente.fotoPerfil
            }

        ref_id = notificacao.referencia_id
        if ref_id is None:
            ref_id = notificacao.idConversa or notificacao.idPostagem or notificacao.idComentario

        link = notificacao.link_acao
        if not link:
            if notificacao.idConversa:
                link = f"/mensagens?chat={notificacao.idConversa}"
            elif notificacao.idPostagem:
                link = "/feed"
            elif notificacao.tipo and str(notificacao.tipo).upper() in ("SEGUIDOR", "FOLLOW"):
                link = "/seguidores"
            else:
                link = "/notificacoes"

        return {
            "id": notificacao.id,
            "usuario_id": notificacao.idUsuario,
            "tipo": notificacao.tipo,
            "titulo": notificacao.titulo,
            "conteudo": notificacao.mensagem,
            "referencia_id": ref_id,
            "link_acao": link,
            "lida": notificacao.lida,
            "criado_em": notificacao.dataCriacao,
            # Campos de compatibilidade
            "idUsuario": notificacao.idUsuario,
            "mensagem": notificacao.mensagem,
            "dataCriacao": notificacao.dataCriacao,
            "idRemetente": notificacao.idRemetente,
            "idPostagem": notificacao.idPostagem,
            "idComentario": notificacao.idComentario,
            "idConversa": notificacao.idConversa,
            "remetente": rem
        }

    @staticmethod
    def listar_notificacoes(db: Session, usuario_id: int) -> List[dict]:
        """
        Retorna todas as notificações ativas do usuário autenticado (mais recentes primeiro).
        """
        itens = NotificacaoRepository.listar_por_usuario(db, usuario_id)
        return [NotificacaoService.serializar_notificacao(n) for n in itens]

    @staticmethod
    def listar_notificacoes_paginadas(
        db: Session,
        usuario_id: int,
        tipo: Optional[str] = None,
        apenas_nao_lidas: bool = False,
        limite: int = 20,
        offset: int = 0
    ) -> dict:
        """
        Lista notificações de forma paginada com suporte a filtros e contadores.
        """
        itens, total, total_nao_lidas = NotificacaoRepository.listar_com_filtros(
            db=db,
            usuario_id=usuario_id,
            tipo=tipo,
            apenas_nao_lidas=apenas_nao_lidas,
            limite=limite,
            offset=offset
        )
        formatados = [NotificacaoService.serializar_notificacao(n) for n in itens]
        return {
            "total_nao_lidas": total_nao_lidas,
            "total": total,
            "notificacoes": formatados,
            "items": formatados  # Retrocompatibilidade
        }


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
            "status": "sucesso",
            "total_atualizadas": qtd,
            "atualizadas": qtd,
            "message": "Todas as notificações foram marcadas como lidas."
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

        return {
            "status": "sucesso",
            "mensagem": "Notificação excluída com sucesso.",
            "message": "Notificação excluída com sucesso."
        }

    @staticmethod
    def deletar_todas(db: Session, usuario_id: int) -> dict:
        """
        Realiza o soft delete de todas as notificações do usuário autenticado.
        """
        qtd = NotificacaoRepository.deletar_todas(db, usuario_id)
        redis_client.delete(f"notificacoes:nao_lidas:{usuario_id}")
        return {
            "status": "sucesso",
            "total_excluidas": qtd,
            "message": "Todas as notificações foram excluídas com sucesso."
        }

