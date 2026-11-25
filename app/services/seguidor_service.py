import json
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.seguidor_model import Seguidor
from app.repositories.seguidor_repository import SeguidorRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.notificacao_service import NotificacaoService
from app.schemas.seguidor_schema import RelacionamentoStatusResposta, UsuarioRelacionamentoItem
from app.redis_client import redis_client


class SeguidorService:
    """
    Serviço contendo as regras de negócio para seguir, deixar de seguir e consultar relacionamentos.
    """

    @staticmethod
    def alternar_seguir(db: Session, seguidor_id: int, seguido_id: int) -> dict:
        """
        Alterna o relacionamento de seguir entre dois usuários:
        - Se seguidor_id == seguido_id: bloqueia com erro 400.
        - Se já existe vínculo: remove (unfollow), commita, invalida cache e retorna {"status": "sucesso", "seguindo": False, "total_seguidores": novo_total} sem disparar notificação.
        - Se não existe vínculo: cria (follow), commita, invalida cache, dispara notificação e evento WebSocket para o seguido e retorna {"status": "sucesso", "seguindo": True, "total_seguidores": novo_total}.
        """
        if seguidor_id == seguido_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode seguir seu próprio perfil."
            )

        usuario_seguido = UsuarioRepository.buscar_por_id(db, seguido_id)
        if not usuario_seguido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        relacao_existente = SeguidorRepository.buscar(db, seguidor_id, seguido_id)

        if relacao_existente:
            # Unfollow: remove o registro do banco
            SeguidorRepository.deletar(db, relacao_existente)

            # Invalidação de cache no Redis
            redis_client.delete(f"artfolio:perfil:{seguidor_id}")
            redis_client.delete(f"artfolio:perfil:{seguido_id}")
            redis_client.delete_pattern("artfolio:obras:*")

            novo_total = SeguidorRepository.contar_por_usuario(db, seguido_id)

            payload_ws = {
                "tipo": "SEGUIDOR",
                "seguido_id": seguido_id,
                "total_seguidores": novo_total,
                "mensagem": "Um usuário deixou de seguir você."
            }
            publicado = False
            try:
                publicado = bool(redis_client.publish(f"notificacoes:{seguido_id}", json.dumps(payload_ws, ensure_ascii=False)))
            except Exception:
                publicado = False
            if not publicado:
                try:
                    from app.core.websocket_manager import manager
                    manager.dispatch_personal_message_sync(seguido_id, payload_ws)
                except Exception:
                    pass

            return {
                "status": "sucesso",
                "seguindo": False,
                "total_seguidores": novo_total
            }
        else:
            # Follow: cria novo relacionamento
            novo_seguidor = Seguidor(
                idSeguidor=seguidor_id,
                idSeguido=seguido_id
            )
            SeguidorRepository.criar(db, novo_seguidor)

            # Invalidação de cache no Redis
            redis_client.delete(f"artfolio:perfil:{seguidor_id}")
            redis_client.delete(f"artfolio:perfil:{seguido_id}")
            redis_client.delete_pattern("artfolio:obras:*")

            novo_total = SeguidorRepository.contar_por_usuario(db, seguido_id)

            remetente = UsuarioRepository.buscar_por_id(db, seguidor_id)
            nome_remetente = remetente.nome if remetente else "Alguém"
            foto_remetente = getattr(remetente, "fotoPerfil", None) if remetente else None

            # 1. Notificação persistente no banco de dados (sem publicar duplicado no WS)
            notificacao = NotificacaoService.criar_notificacao(
                db=db,
                id_usuario=seguido_id,
                tipo="FOLLOW",
                titulo="Novo seguidor",
                mensagem=f"{nome_remetente} começou a seguir você.",
                id_remetente=seguidor_id,
                publicar_ws=False
            )

            # 2. Evento WebSocket em tempo real para sincronização reativa de contadores
            payload_ws = {
                "id": notificacao.id if notificacao else None,
                "tipo": "SEGUIDOR",
                "seguido_id": seguido_id,
                "total_seguidores": novo_total,
                "mensagem": f"{nome_remetente} começou a seguir você.",
                "remetente": {
                    "id": remetente.id if remetente else seguidor_id,
                    "nome": nome_remetente,
                    "fotoPerfil": foto_remetente
                },
                "naoLidasCount": NotificacaoService.contar_nao_lidas(db, seguido_id)
            }
            publicado = False
            try:
                publicado = bool(redis_client.publish(f"notificacoes:{seguido_id}", json.dumps(payload_ws, ensure_ascii=False)))
            except Exception:
                publicado = False
            if not publicado:
                try:
                    from app.core.websocket_manager import manager
                    manager.dispatch_personal_message_sync(seguido_id, payload_ws)
                except Exception:
                    pass

            return {
                "status": "sucesso",
                "seguindo": True,
                "total_seguidores": novo_total
            }

    @staticmethod
    def seguir(db: Session, seguidor_id: int, seguido_id: int):
        """
        Alias compatível para alternar ou registrar relacionamento de seguir.
        """
        return SeguidorService.alternar_seguir(db, seguidor_id, seguido_id)

    @staticmethod
    def deixar_de_seguir(db: Session, seguidor_id: int, seguido_id: int) -> dict:
        """
        Remove o relacionamento de seguir entre dois usuários de maneira defensiva,
        sem estourar 404/500 caso o vínculo já não exista.
        """
        relacao = SeguidorRepository.buscar(db, seguidor_id, seguido_id)
        if relacao:
            SeguidorRepository.deletar(db, relacao)

        redis_client.delete(f"artfolio:perfil:{seguidor_id}")
        redis_client.delete(f"artfolio:perfil:{seguido_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        novo_total = SeguidorRepository.contar_seguidores(db, seguido_id)

        return {
            "status": "sucesso",
            "seguindo": False,
            "total_seguidores": novo_total,
            "message": "Você deixou de seguir este usuário."
        }

    @staticmethod
    def obter_status_relacionamento(db: Session, me_id: int, target_id: int) -> RelacionamentoStatusResposta:
        """
        Retorna o status de relacionamento entre o usuário logado (me_id) e o usuário alvo (target_id).
        """
        is_me = (me_id == target_id)
        seguidores_cnt = SeguidorRepository.contar_seguidores(db, target_id)
        seguindo_cnt = SeguidorRepository.contar_seguindo(db, target_id)

        if is_me:
            return RelacionamentoStatusResposta(
                seguindo=False,
                segueDeVolta=False,
                isMe=True,
                seguidoresCount=seguidores_cnt,
                seguindoCount=seguindo_cnt
            )

        eu_sigo = SeguidorRepository.buscar(db, me_id, target_id) is not None
        ele_me_segue = SeguidorRepository.buscar(db, target_id, me_id) is not None

        return RelacionamentoStatusResposta(
            seguindo=eu_sigo,
            segueDeVolta=ele_me_segue,
            isMe=False,
            seguidoresCount=seguidores_cnt,
            seguindoCount=seguindo_cnt
        )

    @staticmethod
    def listar_seguidores(db: Session, target_id: int, me_id: int) -> List[UsuarioRelacionamentoItem]:
        """
        Retorna a lista de pessoas que seguem o usuário alvo (target_id),
        enriquecida com flags de relacionamento em relação ao usuário logado (me_id).
        """
        from app.services.plano_service import PlanoService
        relacoes = SeguidorRepository.listar_seguidores(db, target_id)
        itens = []
        for rel in relacoes:
            usr = UsuarioRepository.buscar_por_id(db, rel.idSeguidor)
            if usr and not usr.deletado:
                eu_sigo = SeguidorRepository.buscar(db, me_id, usr.id) is not None
                ele_me_segue = SeguidorRepository.buscar(db, usr.id, me_id) is not None
                is_me = (me_id == usr.id)
                plano_usr = PlanoService.obter_tipo_plano_usuario(db, usr.id)
                item = UsuarioRelacionamentoItem(
                    id=usr.id,
                    nome=usr.nome,
                    email=usr.email,
                    fotoPerfil=usr.fotoPerfil,
                    tipo_conta=usr.tipo_conta,
                    biografia=usr.biografia,
                    plano=plano_usr,
                    mostrar_moldura_led=getattr(usr, "mostrar_moldura_led", True),
                    mostrar_badge_plano=getattr(usr, "mostrar_badge_plano", True),
                    cor_led_hex=getattr(usr, "cor_led_hex", "#E17055") or "#E17055",
                    seguindo=eu_sigo,
                    segueDeVolta=ele_me_segue,
                    isMe=is_me
                )
                itens.append(item)
        return itens

    @staticmethod
    def listar_seguindo(db: Session, target_id: int, me_id: int) -> List[UsuarioRelacionamentoItem]:
        """
        Retorna a lista de pessoas que o usuário alvo (target_id) está seguindo,
        enriquecida com flags de relacionamento em relação ao usuário logado (me_id).
        """
        from app.services.plano_service import PlanoService
        relacoes = SeguidorRepository.listar_seguindo(db, target_id)
        itens = []
        for rel in relacoes:
            usr = UsuarioRepository.buscar_por_id(db, rel.idSeguido)
            if usr and not usr.deletado:
                eu_sigo = SeguidorRepository.buscar(db, me_id, usr.id) is not None
                ele_me_segue = SeguidorRepository.buscar(db, usr.id, me_id) is not None
                is_me = (me_id == usr.id)
                plano_usr = PlanoService.obter_tipo_plano_usuario(db, usr.id)
                item = UsuarioRelacionamentoItem(
                    id=usr.id,
                    nome=usr.nome,
                    email=usr.email,
                    fotoPerfil=usr.fotoPerfil,
                    tipo_conta=usr.tipo_conta,
                    biografia=usr.biografia,
                    plano=plano_usr,
                    mostrar_moldura_led=getattr(usr, "mostrar_moldura_led", True),
                    mostrar_badge_plano=getattr(usr, "mostrar_badge_plano", True),
                    cor_led_hex=getattr(usr, "cor_led_hex", "#E17055") or "#E17055",
                    seguindo=eu_sigo,
                    segueDeVolta=ele_me_segue,
                    isMe=is_me
                )
                itens.append(item)
        return itens

