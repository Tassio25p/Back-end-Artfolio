from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.denuncia_model import Denuncia


class DenunciaRepository:
    """
    Repositório de dados para a entidade Denuncia.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def buscar(db: Session, usuario_id: int, postagem_id: int) -> Optional[Denuncia]:
        """
        Busca uma denúncia ativa enviada por um determinado usuário para uma determinada postagem.
        """
        return db.query(Denuncia).filter(
            Denuncia.idUsuario == usuario_id,
            Denuncia.idPostagem == postagem_id
        ).first()

    @staticmethod
    def buscar_por_id(db: Session, denuncia_id: int) -> Optional[Denuncia]:
        """
        Busca uma denúncia pelo seu ID.
        """
        return db.query(Denuncia).filter(Denuncia.id == denuncia_id).first()

    @staticmethod
    def criar(db: Session, denuncia: Denuncia) -> Denuncia:
        """
        Persiste uma nova denúncia no banco de dados.
        """
        db.add(denuncia)
        db.commit()
        db.refresh(denuncia)
        return denuncia

    @staticmethod
    def listar_todas(db: Session) -> List[Denuncia]:
        """
        Lista todas as denúncias cadastradas (mais recentes primeiro).
        """
        return db.query(Denuncia).order_by(Denuncia.dataCriacao.desc()).all()

    @staticmethod
    def atualizar_status(db: Session, denuncia: Denuncia, novo_status: str) -> Denuncia:
        """
        Atualiza o status de moderação de uma denúncia.
        """
        denuncia.status = novo_status
        db.commit()
        db.refresh(denuncia)
        return denuncia
