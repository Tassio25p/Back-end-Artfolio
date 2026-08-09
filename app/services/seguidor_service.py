from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.seguidor_model import Seguidor
from app.repositories.seguidor_repository import SeguidorRepository
from app.repositories.usuario_repository import UsuarioRepository


class SeguidorService:
    """
    Serviço contendo as regras de negócio para seguir/deixar de seguir.
    """

    @staticmethod
    def seguir(db: Session, seguidor_id: int, seguido_id: int) -> Seguidor:
        """
        Registra que um usuário passou a seguir outro.

        Valida que o usuário não está seguindo a si mesmo,
        que o usuário a ser seguido existe e não está deletado,
        e que não existe relacionamento duplicado.

        Args:
            db: Sessão ativa do SQLAlchemy.
            seguidor_id: ID do usuário que quer seguir (do JWT).
            seguido_id: ID do usuário a ser seguido.

        Returns:
            O objeto Seguidor criado.

        Raises:
            HTTPException 400: Se tentar seguir a si mesmo ou já seguir.
            HTTPException 404: Se o usuário a ser seguido não existir.
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
        return SeguidorRepository.criar(db, novo_seguidor)

    @staticmethod
    def deixar_de_seguir(db: Session, seguidor_id: int, seguido_id: int) -> dict:
        """
        Remove o relacionamento de seguir entre dois usuários.

        Args:
            db: Sessão ativa do SQLAlchemy.
            seguidor_id: ID do usuário que quer deixar de seguir (do JWT).
            seguido_id: ID do usuário a ser deixado de seguir.

        Returns:
            Dicionário com mensagem de sucesso.

        Raises:
            HTTPException 404: Se o relacionamento não existir.
        """
        relacao = SeguidorRepository.buscar(db, seguidor_id, seguido_id)
        if not relacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Você não está seguindo este usuário."
            )

        SeguidorRepository.deletar(db, relacao)
        return {"message": "Você deixou de seguir este usuário."}
