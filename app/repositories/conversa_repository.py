from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario

class ConversaRepository:
    """
    Repositório de dados para as entidades Conversa e ConversaUsuario.

    Encapsula consultas e operações de persistência relacionadas às conversas
    e participantes no PostgreSQL utilizando SQLAlchemy.
    """

    @staticmethod
    def buscar_por_id(db: Session, conversa_id: int) -> Optional[Conversa]:
        """
        Busca uma conversa ativa pelo seu ID.
        """
        return db.query(Conversa).filter(
            Conversa.id == conversa_id,
            Conversa.deletado == False
        ).first()

    @staticmethod
    def buscar_conversa_entre_usuarios(db: Session, usuario_1_id: int, usuario_2_id: int) -> Optional[Conversa]:
        """
        Verifica se já existe uma conversa ativa vinculando exatamente os dois usuários informados.
        """
        subq = (
            db.query(ConversaUsuario.idConversa)
            .filter(ConversaUsuario.idUsuario.in_([usuario_1_id, usuario_2_id]))
            .group_by(ConversaUsuario.idConversa)
            .having(func.count(ConversaUsuario.idUsuario.distinct()) == 2)
            .subquery()
        )
        return db.query(Conversa).filter(
            Conversa.id.in_(subq),
            Conversa.deletado == False
        ).first()

    @staticmethod
    def listar_conversas_usuario(db: Session, usuario_id: int) -> List[Conversa]:
        """
        Retorna a lista de todas as conversas ativas em que o usuário informado participa ativamente.
        """
        return (
            db.query(Conversa)
            .join(ConversaUsuario, ConversaUsuario.idConversa == Conversa.id)
            .filter(
                ConversaUsuario.idUsuario == usuario_id,
                ConversaUsuario.deletado == False,
                Conversa.deletado == False
            )
            .all()
        )

    @staticmethod
    def usuario_participa(db: Session, conversa_id: int, usuario_id: int) -> bool:
        """
        Verifica se o usuário é participante ativo da conversa informada.
        """
        registro = db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id,
            ConversaUsuario.idUsuario == usuario_id,
            ConversaUsuario.deletado == False
        ).first()
        return registro is not None

    @staticmethod
    def buscar_participantes(db: Session, conversa_id: int) -> List[ConversaUsuario]:
        """
        Retorna os registros de participantes da conversa.
        """
        return db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id
        ).all()

    @staticmethod
    def criar_conversa(db: Session, usuario_1_id: int, usuario_2_id: int) -> Conversa:
        """
        Cria uma nova conversa e associa os dois usuários como participantes.
        """
        nova_conversa = Conversa()
        db.add(nova_conversa)
        db.commit()
        db.refresh(nova_conversa)

        cu1 = ConversaUsuario(idConversa=nova_conversa.id, idUsuario=usuario_1_id)
        cu2 = ConversaUsuario(idConversa=nova_conversa.id, idUsuario=usuario_2_id)
        db.add_all([cu1, cu2])
        db.commit()

        return nova_conversa

    @staticmethod
    def reativar_participacao(db: Session, conversa_id: int, usuario_id: int):
        """
        Caso a conversa estivesse ocultada/deletada para um dos usuários, reativa o registro.
        """
        registro = db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id,
            ConversaUsuario.idUsuario == usuario_id
        ).first()

        if registro and registro.deletado:
            registro.deletado = False
            registro.dataDelecao = None
            db.commit()

    @staticmethod
    def ocultar_conversa_usuario(db: Session, conversa_id: int, usuario_id: int):
        """
        Oculta a conversa exclusivamente para o usuário especificado (soft delete em ConversaUsuario).
        """
        registro = db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id,
            ConversaUsuario.idUsuario == usuario_id
        ).first()

        if registro:
            registro.deletado = True
            registro.dataDelecao = func.now()
            db.commit()
