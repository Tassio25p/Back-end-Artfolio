from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.postagem_model import Postagem
from app.models.postagem_categoria_model import PostagemCategoria

class PostagemRepository:
    """
    Repositório de dados para a entidade Postagem (Obras).
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL com suporte a N:N categorias.
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
        categoria_id: Optional[int] = None,
        termo_busca: Optional[str] = None
    ) -> List[Postagem]:
        """
        Lista todas as obras ativas no sistema.
        Permite filtragem opcional por usuário (artista), por categoria (N:N) e por termo.
        """
        query = db.query(Postagem).filter(Postagem.deletado == False)

        if usuario_id is not None:
            query = query.filter(Postagem.idUsuario == usuario_id)

        if categoria_id is not None:
            query = query.filter(
                Postagem.postagem_categorias.any(PostagemCategoria.idCategoria == categoria_id)
            )

        if termo_busca:
            busca_like = f"%{termo_busca}%"
            query = query.filter(Postagem.legenda.ilike(busca_like))

        return query.order_by(Postagem.dataPostagem.desc()).all()

    @staticmethod
    def vincular_categorias(db: Session, postagem_id: int, categoria_ids: List[int]) -> None:
        """
        Vincula uma lista de IDs de categorias à postagem na tabela postagem_categoria.
        """
        db.query(PostagemCategoria).filter(PostagemCategoria.idPostagem == postagem_id).delete()
        for cat_id in set(categoria_ids):
            db.add(PostagemCategoria(idPostagem=postagem_id, idCategoria=cat_id))
        db.commit()

    @staticmethod
    def criar(db: Session, postagem: Postagem, categoria_ids: Optional[List[int]] = None) -> Postagem:
        """
        Persiste uma nova postagem no banco de dados e vincula suas categorias na tabela intermediária.
        """
        db.add(postagem)
        db.commit()
        db.refresh(postagem)

        if categoria_ids:
            for cat_id in set(categoria_ids):
                db.add(PostagemCategoria(idPostagem=postagem.id, idCategoria=cat_id))
            db.commit()
            db.refresh(postagem)

        return postagem

    @staticmethod
    def atualizar(db: Session, postagem: Postagem, categoria_ids: Optional[List[int]] = None) -> Postagem:
        """
        Salva as alterações de uma postagem existente no banco de dados.
        """
        if categoria_ids is not None:
            db.query(PostagemCategoria).filter(PostagemCategoria.idPostagem == postagem.id).delete()
            for cat_id in set(categoria_ids):
                db.add(PostagemCategoria(idPostagem=postagem.id, idCategoria=cat_id))

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
