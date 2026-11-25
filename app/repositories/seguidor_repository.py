from typing import Optional
from sqlalchemy.orm import Session
from app.models.seguidor_model import Seguidor
from app.models.usuario_model import Usuario

class SeguidorRepository:
    """
    Repositório de dados para a entidade Seguidor.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL com chave composta.
    Garante que contas excluídas não contem nos seguidores e seguindo.
    """

    @staticmethod
    def buscar(db: Session, seguidor_id: int, seguido_id: int) -> Optional[Seguidor]:
        """
        Verifica se um usuário já segue outro.
        """
        return db.query(Seguidor).filter(
            Seguidor.idSeguidor == seguidor_id,
            Seguidor.idSeguido == seguido_id
        ).first()

    @staticmethod
    def criar(db: Session, seguidor: Seguidor) -> Seguidor:
        """
        Persiste um novo relacionamento de seguir no banco de dados.
        """
        db.add(seguidor)
        db.commit()
        db.refresh(seguidor)
        return seguidor

    @staticmethod
    def deletar(db: Session, seguidor: Seguidor) -> None:
        """
        Remove o relacionamento de seguir do banco de dados.
        """
        db.delete(seguidor)
        db.commit()

    @staticmethod
    def contar_seguidores(db: Session, usuario_id: int) -> int:
        """
        Conta quantas pessoas ativas seguem um usuário específico.
        """
        return db.query(Seguidor).join(
            Usuario, Usuario.id == Seguidor.idSeguidor
        ).filter(
            Seguidor.idSeguido == usuario_id,
            Usuario.deletado == False
        ).count()

    # Alias para compatibilidade
    contar_por_usuario = contar_seguidores

    @staticmethod
    def contar_seguindo(db: Session, usuario_id: int) -> int:
        """
        Conta quantas pessoas ativas um usuário está seguindo.
        """
        return db.query(Seguidor).join(
            Usuario, Usuario.id == Seguidor.idSeguido
        ).filter(
            Seguidor.idSeguidor == usuario_id,
            Usuario.deletado == False
        ).count()

    @staticmethod
    def listar_seguidores(db: Session, usuario_id: int):
        """
        Retorna a lista de relacionamentos onde idSeguido == usuario_id com usuários ativos.
        """
        return db.query(Seguidor).join(
            Usuario, Usuario.id == Seguidor.idSeguidor
        ).filter(
            Seguidor.idSeguido == usuario_id,
            Usuario.deletado == False
        ).order_by(Seguidor.dataSeguiu.desc()).all()

    @staticmethod
    def listar_seguindo(db: Session, usuario_id: int):
        """
        Retorna a lista de relacionamentos onde idSeguidor == usuario_id com usuários ativos.
        """
        return db.query(Seguidor).join(
            Usuario, Usuario.id == Seguidor.idSeguido
        ).filter(
            Seguidor.idSeguidor == usuario_id,
            Usuario.deletado == False
        ).order_by(Seguidor.dataSeguiu.desc()).all()
