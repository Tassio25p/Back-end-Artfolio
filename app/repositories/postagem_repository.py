from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.postagem_model import Postagem

class PostagemRepository:
    """
    Repositório de dados para a entidade Postagem (Obras).
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def buscar_por_id(db: Session, postagem_id: int) -> Optional[Postagem]:
        """
        Busca uma obra ativa pelo seu ID.
        """
        return db.query(Postagem).filter(
            Postagem.id == postagem_id,
            Postagem.deletado == False
        ).first()

    @staticmethod
    def listar_todas(
        db: Session,
        usuario_id: Optional[int] = None,
        categoria_id: Optional[int] = None
    ) -> List[Postagem]:
        """
        Lista todas as obras ativas no sistema.
        Permite filtragem opcional por usuário (artista) e por categoria.
        """
        query = db.query(Postagem).filter(Postagem.deletado == False)

        if usuario_id is not None:
            query = query.filter(Postagem.idUsuario == usuario_id)

        if categoria_id is not None:
            query = query.filter(Postagem.idCategoria == categoria_id)

        return query.order_by(Postagem.dataPostagem.desc()).all()

    @staticmethod
    def criar(db: Session, postagem: Postagem) -> Postagem:
        """
        Persiste uma nova postagem no banco de dados.
        """
        db.add(postagem)
        db.commit()
        db.refresh(postagem)
        return postagem

    @staticmethod
    def atualizar(db: Session, postagem: Postagem) -> Postagem:
        """
        Salva as alterações de uma postagem existente no banco de dados.
        """
        db.commit()
        db.refresh(postagem)
        return postagem

    @staticmethod
    def deletar(db: Session, postagem: Postagem) -> None:
        """
        Realiza o soft delete de uma postagem, marcando-a como deletada.
        """
        postagem.deletado = True
        postagem.dataDelecao = datetime.utcnow()
        db.commit()
