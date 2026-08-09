from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.obra_salva_model import ObraSalva
from app.repositories.obra_salva_repository import ObraSalvaRepository
from app.repositories.postagem_repository import PostagemRepository
from app.schemas.postagem_schema import PostagemResposta


class ObraSalvaService:
    """
    Serviço contendo as regras de negócio para salvamento de obras.
    """

    @staticmethod
    def salvar_obra(db: Session, usuario_id: int, postagem_id: int) -> ObraSalva:
        """
        Registra que o usuário logado salvou a obra especificada.

        Valida se a postagem existe.
        Garante não-duplicidade (retorna HTTP 400 se já estiver salva).

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (JWT).
            postagem_id: ID da obra/postagem.

        Returns:
            Objeto ObraSalva criado.

        Raises:
            HTTPException 404: Postagem não encontrada.
            HTTPException 400: Obra já salva pelo usuário.
        """
        postagem = PostagemRepository.buscar_por_id(db, postagem_id)
        if not postagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postagem não encontrada."
            )

        ja_salva = ObraSalvaRepository.buscar(db, usuario_id, postagem_id)
        if ja_salva:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você já salvou esta obra."
            )

        nova_obra_salva = ObraSalva(idUsuario=usuario_id, idPostagem=postagem_id)
        return ObraSalvaRepository.criar(db, nova_obra_salva)

    @staticmethod
    def remover_salvo(db: Session, usuario_id: int, postagem_id: int) -> dict:
        """
        Remover o salvamento de uma obra para o usuário logado.

        Raises:
            HTTPException 404: Se o salvamento não for encontrado.
        """
        obra_salva = ObraSalvaRepository.buscar(db, usuario_id, postagem_id)
        if not obra_salva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Esta obra não está nos seus salvos."
            )

        ObraSalvaRepository.deletar(db, obra_salva)
        return {"message": "Obra removida dos salvos com sucesso.", "salvo": False}

    @staticmethod
    def checar_salvo(db: Session, usuario_id: int, postagem_id: int) -> dict:
        """
        Verifica se a obra está salva pelo usuário logado.
        """
        esta_salva = ObraSalvaRepository.buscar(db, usuario_id, postagem_id) is not None
        return {"salvo": esta_salva}

    @staticmethod
    def listar_salvas(db: Session, usuario_id: int) -> List[PostagemResposta]:
        """
        Retorna a lista de postagens/obras salvas pelo usuário logado.
        """
        salvos = ObraSalvaRepository.listar_por_usuario(db, usuario_id)
        postagens = []
        for s in salvos:
            if s.postagem and not s.postagem.deletado:
                postagens.append(PostagemResposta.model_validate(s.postagem))
        return postagens
