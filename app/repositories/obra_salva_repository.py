from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.obra_salva_model import ObraSalva


class ObraSalvaRepository:
    """
    Repositório de dados para a entidade ObraSalva.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def buscar(db: Session, usuario_id: int, postagem_id: int) -> Optional[ObraSalva]:
        """
        Busca o registro de salvamento de uma postagem por um determinado usuário.
        """
        return db.query(ObraSalva).filter(
            ObraSalva.idUsuario == usuario_id,
            ObraSalva.idPostagem == postagem_id
        ).first()

    @staticmethod
    def contar_por_postagem(db: Session, postagem_id: int) -> int:
        """
        Retorna o total de vezes que uma obra foi salva/favoritada.
        """
        return db.query(ObraSalva).filter(ObraSalva.idPostagem == postagem_id).count()

    @staticmethod
    def criar(db: Session, obra_salva: ObraSalva) -> ObraSalva:
        """
        Persiste o registro de salvamento de uma obra no banco de dados.
        """
        db.add(obra_salva)
        db.commit()
        db.refresh(obra_salva)
        return obra_salva

    @staticmethod
    def deletar(db: Session, obra_salva: ObraSalva) -> None:
        """
        Remove o registro de salvamento de uma obra no banco de dados.
        """
        db.delete(obra_salva)
        db.commit()

    @staticmethod
    def listar_por_usuario(db: Session, usuario_id: int) -> List[ObraSalva]:
        """
        Lista todas as obras salvas pelo usuário autenticado (ordenadas das mais recentes para as mais antigas).
        """
        return db.query(ObraSalva).filter(
            ObraSalva.idUsuario == usuario_id
        ).order_by(ObraSalva.dataCriacao.desc()).all()
