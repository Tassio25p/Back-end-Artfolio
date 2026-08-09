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
    def seguir(db: Session, seguidor_id: int, seguido_id: int) -> Seguidor:
        """
        Registra que um usuário passou a seguir outro.
        """
        # 1. Não permitir seguir a si mesmo
        if seguidor_id == seguido_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode seguir a si mesmo."
            )

        # 2. Verificar se o usuário a ser seguido existe e está ativo
        usuario_seguido = UsuarioRepository.buscar_por_id(db, seguido_id)
        if not usuario_seguido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # 3. Verificar se já segue
        relacao_existente = SeguidorRepository.buscar(db, seguidor_id, seguido_id)
        if relacao_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você já está seguindo este usuário."
            )

        # 4. Criar o relacionamento
        novo_seguidor = Seguidor(
            idSeguidor=seguidor_id,
            idSeguido=seguido_id
        )
        seguidor_salvo = SeguidorRepository.criar(db, novo_seguidor)

        # 5. Invalidar caches do Redis
        redis_client.delete(f"artfolio:perfil:{seguidor_id}")
        redis_client.delete(f"artfolio:perfil:{seguido_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        # 6. Disparar notificação automática para o usuário seguido
        remetente = UsuarioRepository.buscar_por_id(db, seguidor_id)
        nome_remetente = remetente.nome if remetente else "Alguém"
        NotificacaoService.criar_notificacao(
            db=db,
            id_usuario=seguido_id,
            tipo="FOLLOW",
            titulo="Novo seguidor",
            mensagem=f"{nome_remetente} começou a seguir você.",
            id_remetente=seguidor_id
        )

        return seguidor_salvo

    @staticmethod
    def deixar_de_seguir(db: Session, seguidor_id: int, seguido_id: int) -> dict:
        """
        Remove o relacionamento de seguir entre dois usuários.
        """
        relacao = SeguidorRepository.buscar(db, seguidor_id, seguido_id)
        if not relacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Você não está seguindo este usuário."
            )

        SeguidorRepository.deletar(db, relacao)

        # Invalidar caches do Redis
        redis_client.delete(f"artfolio:perfil:{seguidor_id}")
        redis_client.delete(f"artfolio:perfil:{seguido_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        return {"message": "Você deixou de seguir este usuário."}

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
        relacoes = SeguidorRepository.listar_seguidores(db, target_id)
        itens = []
        for rel in relacoes:
            usr = UsuarioRepository.buscar_por_id(db, rel.idSeguidor)
            if usr and not usr.deletado:
                eu_sigo = SeguidorRepository.buscar(db, me_id, usr.id) is not None
                ele_me_segue = SeguidorRepository.buscar(db, usr.id, me_id) is not None
                is_me = (me_id == usr.id)
                item = UsuarioRelacionamentoItem(
                    id=usr.id,
                    nome=usr.nome,
                    email=usr.email,
                    fotoPerfil=usr.fotoPerfil,
                    tipo_conta=usr.tipo_conta,
                    biografia=usr.biografia,
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
        relacoes = SeguidorRepository.listar_seguindo(db, target_id)
        itens = []
        for rel in relacoes:
            usr = UsuarioRepository.buscar_por_id(db, rel.idSeguido)
            if usr and not usr.deletado:
                eu_sigo = SeguidorRepository.buscar(db, me_id, usr.id) is not None
                ele_me_segue = SeguidorRepository.buscar(db, usr.id, me_id) is not None
                is_me = (me_id == usr.id)
                item = UsuarioRelacionamentoItem(
                    id=usr.id,
                    nome=usr.nome,
                    email=usr.email,
                    fotoPerfil=usr.fotoPerfil,
                    tipo_conta=usr.tipo_conta,
                    biografia=usr.biografia,
                    seguindo=eu_sigo,
                    segueDeVolta=ele_me_segue,
                    isMe=is_me
                )
                itens.append(item)
        return itens

