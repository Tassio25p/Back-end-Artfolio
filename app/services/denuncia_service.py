from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.denuncia_model import Denuncia
from app.repositories.denuncia_repository import DenunciaRepository
from app.repositories.postagem_repository import PostagemRepository
from app.schemas.denuncia_schema import DenunciaCriar, DenunciaResposta, DenunciaAtualizarStatus


class DenunciaService:
    """
    Serviço contendo as regras de negócio para denúncias de obras.
    """

    @staticmethod
    def criar_denuncia(
        db: Session,
        usuario_id: int,
        postagem_id: int,
        dados: DenunciaCriar
    ) -> Denuncia:
        """
        Cria uma nova denúncia para a obra indicada.

        Regras:
        - Postagem deve existir.
        - O autor da postagem NÃO pode denunciar sua própria obra.
        - O usuário não pode denunciar a mesma postagem duas vezes.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário denunciante (JWT).
            postagem_id: ID da obra/postagem.
            dados: Motivo e descrição opcional.

        Returns:
            Objeto Denuncia criado.
        """
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        if postagem.idUsuario == usuario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode denunciar sua própria obra."
            )

        denuncia_existente = DenunciaRepository.buscar(db, usuario_id, postagem_id)
        if denuncia_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você já denunciou esta obra."
            )

        nova_denuncia = Denuncia(
            idUsuario=usuario_id,
            idPostagem=postagem_id,
            motivo=dados.motivo.strip(),
            descricao=dados.descricao.strip() if dados.descricao else None,
            status="PENDENTE"
        )
        return DenunciaRepository.criar(db, nova_denuncia)

    @staticmethod
    def listar_denuncias(db: Session, usuario_tipo: str) -> List[Denuncia]:
        """
        Lista todas as denúncias para moderadores e administradores.

        Raises:
            HTTPException 403: Se o usuário não for admin ou moderador.
        """
        if usuario_tipo not in ["admin", "moderador"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores e moderadores podem acessar a central de denúncias."
            )

        return DenunciaRepository.listar_todas(db)

    @staticmethod
    def atualizar_status(
        db: Session,
        denuncia_id: int,
        dados: DenunciaAtualizarStatus,
        usuario_tipo: str
    ) -> Denuncia:
        """
        Atualiza o status de uma denúncia.
        """
        if usuario_tipo not in ["admin", "moderador"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores e moderadores podem alterar denúncias."
            )

        denuncia = DenunciaRepository.buscar_por_id(db, denuncia_id)
        if not denuncia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Denúncia não encontrada."
            )

        status_validos = ["PENDENTE", "EM_ANALISE", "RESOLVIDA", "REJEITADA"]
        novo_status = dados.status.upper()
        if novo_status not in status_validos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido. Use um dos seguintes: {', '.join(status_validos)}"
            )

        return DenunciaRepository.atualizar_status(db, denuncia, novo_status)
