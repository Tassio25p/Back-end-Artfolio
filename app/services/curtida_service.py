from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.curtida_model import Curtida
from app.repositories.curtida_repository import CurtidaRepository
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.notificacao_service import NotificacaoService


class CurtidaService:
    """
    Serviço contendo as regras de negócio para curtidas (likes).
    """

    @staticmethod
    def curtir(db: Session, usuario_id: int, postagem_id: int) -> Curtida:
        """
        Registra a curtida de um usuário em uma postagem.

        Valida se a postagem existe e não está deletada.
        Verifica se o usuário já curtiu para evitar duplicatas.
        Cria notificação automática para o proprietário da obra.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (do JWT).
            postagem_id: ID da postagem a ser curtida.

        Returns:
            O objeto Curtida criado.

        Raises:
            HTTPException 404: Se a postagem não for encontrada.
            HTTPException 400: Se o usuário já curtiu a postagem.
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

        # 4. Disparar notificação automática ao autor da obra
        remetente = UsuarioRepository.buscar_por_id(db, usuario_id)
        nome_remetente = remetente.nome if remetente else "Alguém"
        NotificacaoService.criar_notificacao(
            db=db,
            id_usuario=postagem.idUsuario,
            tipo="LIKE",
            titulo="Nova curtida",
            mensagem=f"{nome_remetente} curtiu sua obra.",
            id_remetente=usuario_id,
            id_postagem=postagem_id
        )

        return curtida_salva

    @staticmethod
    def descurtir(db: Session, usuario_id: int, postagem_id: int) -> dict:
        """
        Remove a curtida de um usuário em uma postagem.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (do JWT).
            postagem_id: ID da postagem.

        Returns:
            Dicionário com mensagem de sucesso.

        Raises:
            HTTPException 404: Se a curtida não for encontrada.
        """
        curtida = CurtidaRepository.buscar(db, usuario_id, postagem_id)
        if not curtida:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curtida não encontrada."
            )

        CurtidaRepository.deletar(db, curtida)
        return {"message": "Curtida removida com sucesso."}
