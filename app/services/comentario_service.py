from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.comentario_model import Comentario
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.comentario_schema import ComentarioCriar
from app.services.notificacao_service import NotificacaoService


class ComentarioService:
    """
    Serviço contendo as regras de negócio para comentários.
    """

    @staticmethod
    def criar_comentario(
        db: Session,
        usuario_id: int,
        postagem_id: int,
        dados: ComentarioCriar
    ) -> Comentario:
        """
        Cria um novo comentário em uma postagem.

        Valida se a postagem existe e não está deletada.
        Dispara notificação para o proprietário da obra.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (do JWT).
            postagem_id: ID da postagem a ser comentada.
            dados: Schema com o conteúdo do comentário.

        Returns:
            O objeto Comentario criado com dados do usuário.

        Raises:
            HTTPException 404: Se a postagem não for encontrada.
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

        # 3. Disparar notificação automática ao autor da obra
        remetente = UsuarioRepository.buscar_por_id(db, usuario_id)
        nome_remetente = remetente.nome if remetente else "Alguém"
        NotificacaoService.criar_notificacao(
            db=db,
            id_usuario=postagem.idUsuario,
            tipo="COMMENT",
            titulo="Novo comentário",
            mensagem=f"{nome_remetente} comentou na sua obra.",
            id_remetente=usuario_id,
            id_postagem=postagem_id,
            id_comentario=comentario_salvo.id
        )

        return comentario_salvo

    @staticmethod
    def listar_comentarios(db: Session, postagem_id: int) -> List[Comentario]:
        """
        Lista todos os comentários ativos de uma postagem.

        Valida se a postagem existe antes de listar.

        Args:
            db: Sessão ativa do SQLAlchemy.
            postagem_id: ID da postagem.

        Returns:
            Lista de objetos Comentario com dados dos usuários.

        Raises:
            HTTPException 404: Se a postagem não for encontrada.
        """
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        return ComentarioRepository.listar_por_postagem(db, postagem_id)

    @staticmethod
    def deletar_comentario(
        db: Session,
        usuario_id: int,
        comentario_id: int,
        tipo_conta: str
    ) -> dict:
        """
        Exclui um comentário (soft delete).

        O usuário só pode excluir o próprio comentário.
        Moderadores e admins podem excluir qualquer comentário.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (do JWT).
            comentario_id: ID do comentário a ser excluído.
            tipo_conta: Tipo de conta do usuário autenticado.

        Returns:
            Dicionário com mensagem de sucesso.

        Raises:
            HTTPException 404: Se o comentário não for encontrado.
            HTTPException 403: Se o usuário não tiver permissão.
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

        # 3. Soft delete
        ComentarioRepository.deletar(db, comentario)
        return {"message": "Comentário excluído com sucesso."}
