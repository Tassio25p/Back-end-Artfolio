from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, select, or_
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
            or_(Conversa.deletado == False, Conversa.deletado.is_(None))
        ).first()

    @staticmethod
    def buscar_conversa_entre_usuarios(db: Session, usuario_1_id: int, usuario_2_id: int) -> Optional[Conversa]:
        """
        Verifica se já existe uma conversa ativa vinculando exatamente os dois usuários informados.
        """
        subq = (
            select(ConversaUsuario.idConversa)
            .where(
                ConversaUsuario.idUsuario.in_([usuario_1_id, usuario_2_id]),
                or_(ConversaUsuario.deletado == False, ConversaUsuario.deletado.is_(None))
            )
            .group_by(ConversaUsuario.idConversa)
            .having(func.count(ConversaUsuario.idUsuario.distinct()) == 2)
        )
        return db.query(Conversa).filter(
            Conversa.id.in_(subq),
            or_(Conversa.deletado == False, Conversa.deletado.is_(None))
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
                or_(ConversaUsuario.deletado == False, ConversaUsuario.deletado.is_(None)),
                or_(Conversa.deletado == False, Conversa.deletado.is_(None))
            )
            .order_by(Conversa.id.desc())
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
            or_(ConversaUsuario.deletado == False, ConversaUsuario.deletado.is_(None))
        ).first()
        return registro is not None

    @staticmethod
    def buscar_participantes(db: Session, conversa_id: int) -> List[ConversaUsuario]:
        """
        Retorna os registros de participantes da conversa.
        """
        return db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id,
            or_(ConversaUsuario.deletado == False, ConversaUsuario.deletado.is_(None))
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
    def criar_conversa_grupo(db: Session, admin_id: int, participantes_ids: List[int], nome_grupo: Optional[str] = None) -> Conversa:
        """
        Cria um novo chat em grupo (máx. 12 membros) e associa todos os participantes.
        """
        todos_ids = list(dict.fromkeys([admin_id] + [pid for pid in participantes_ids if pid]))
        nome_final = (nome_grupo.strip() if nome_grupo else None) or f"Grupo ({len(todos_ids)} membros)"

        nova_conversa = Conversa(
            is_grupo=True,
            nome_grupo=nome_final,
            admin_id=admin_id
        )
        db.add(nova_conversa)
        db.commit()
        db.refresh(nova_conversa)

        membros = [ConversaUsuario(idConversa=nova_conversa.id, idUsuario=uid) for uid in todos_ids]
        db.add_all(membros)
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

    @staticmethod
    def atualizar_grupo(db: Session, conversa_id: int, nome_grupo: Optional[str] = None, foto_grupo: Optional[str] = None) -> Conversa:
        """
        Atualiza o nome e/ou foto de um grupo existente.
        """
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id, Conversa.deletado == False).first()
        if conversa:
            if nome_grupo is not None:
                conversa.nome_grupo = nome_grupo.strip()
            if foto_grupo is not None:
                conversa.foto_grupo = foto_grupo.strip() if foto_grupo else None
            db.commit()
            db.refresh(conversa)
        return conversa

    @staticmethod
    def remover_participante_grupo(db: Session, conversa_id: int, usuario_id: int):
        """
        Remove permanentemente o participante do grupo especificado.
        """
        db.query(ConversaUsuario).filter(
            ConversaUsuario.idConversa == conversa_id,
            ConversaUsuario.idUsuario == usuario_id
        ).delete(synchronize_session=False)
        db.commit()

    @staticmethod
    def excluir_grupo(db: Session, conversa_id: int):
        """
        Aplica soft delete na conversa em grupo e remove seus registros de participação.
        """
        conversa = db.query(Conversa).filter(Conversa.id == conversa_id).first()
        if conversa:
            conversa.deletado = True
            conversa.dataDelecao = func.now()
            db.query(ConversaUsuario).filter(ConversaUsuario.idConversa == conversa_id).delete(synchronize_session=False)
            db.commit()