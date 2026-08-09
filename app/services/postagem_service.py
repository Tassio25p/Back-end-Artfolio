from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.postagem_model import Postagem
from app.repositories.postagem_repository import PostagemRepository
from app.schemas.postagem_schema import PostagemCriar, PostagemAtualizar

class PostagemService:
    """
    Serviço contendo as regras de negócio relacionadas às Obras (Postagens).
    """

    @staticmethod
    def listar_obras(
        db: Session,
        usuario_id: Optional[int] = None,
        categoria_id: Optional[int] = None
    ) -> List[Postagem]:
        """
        Retorna a lista de obras ativas no sistema, aplicando os filtros caso fornecidos.
        """
        return PostagemRepository.listar_todas(db, usuario_id=usuario_id, categoria_id=categoria_id)

    @staticmethod
    def buscar_obra_por_id(db: Session, postagem_id: int) -> Postagem:
        """
        Busca uma obra pelo ID. Lança exceção HTTP 404 se a obra não for encontrada ou estiver deletada.
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )
        return obra

    @staticmethod
    def criar_postagem(db: Session, usuario_id: int, dados: PostagemCriar) -> Postagem:
        """
        Cria e persiste uma nova postagem no banco de dados.
        O idUsuario é fornecido obrigatoriamente pelo token JWT do usuário autenticado.
        """
        nova_postagem = Postagem(
            idUsuario=usuario_id,
            idCategoria=dados.idCategoria,
            legenda=dados.legenda,
            arquivoUrl=dados.arquivoUrl,
        )
        return PostagemRepository.criar(db, nova_postagem)

    @staticmethod
    def atualizar_postagem(db: Session, postagem_id: int, usuario_id: int, dados: PostagemAtualizar) -> Postagem:
        """
        Atualiza os campos informados de uma postagem existente.
        Valida que apenas o proprietário da postagem pode editá-la (HTTP 403 se não for o dono).
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        if obra.idUsuario != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta postagem."
            )

        if dados.idCategoria is not None:
            obra.idCategoria = dados.idCategoria
        if dados.legenda is not None:
            obra.legenda = dados.legenda
        if dados.arquivoUrl is not None:
            obra.arquivoUrl = dados.arquivoUrl

        return PostagemRepository.atualizar(db, obra)

    @staticmethod
    def deletar_postagem(db: Session, postagem_id: int, usuario_id: int, tipo_conta: str = "cliente") -> None:
        """
        Realiza o soft delete de uma postagem.
        Apenas o proprietário ou moderadores/admins podem excluir a postagem.
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        tipos_admin = ["admin", "moderador"]
        if obra.idUsuario != usuario_id and tipo_conta not in tipos_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para excluir esta postagem."
            )

        PostagemRepository.deletar(db, obra)
