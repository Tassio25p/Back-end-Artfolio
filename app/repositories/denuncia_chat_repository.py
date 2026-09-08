from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.denuncia_chat_model import DenunciaChat

class DenunciaChatRepository:
    """
    Repositório de dados para a entidade DenunciaChat no PostgreSQL.
    """

    @staticmethod
    def criar(db: Session, denuncia: DenunciaChat) -> DenunciaChat:
        """
        Salva uma nova denúncia no banco de dados.
        """
        db.add(denuncia)
        db.commit()
        db.refresh(denuncia)
        return denuncia

    @staticmethod
    def buscar_por_id(db: Session, denuncia_id: int) -> Optional[DenunciaChat]:
        """
        Busca uma denúncia pelo ID.
        """
        return db.query(DenunciaChat).filter(DenunciaChat.id == denuncia_id).first()

    @staticmethod
    def listar_por_conversa(db: Session, conversa_id: int) -> List[DenunciaChat]:
        """
        Lista todas as denúncias de uma determinada conversa.
        """
        return db.query(DenunciaChat).filter(DenunciaChat.conversa_id == conversa_id).all()
