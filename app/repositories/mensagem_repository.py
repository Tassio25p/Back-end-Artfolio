from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.mensagem_model import Mensagem

class MensagemRepository:
    """
    Repositório de dados para a entidade Mensagem.

    Encapsula consultas e operações de persistência relacionadas às mensagens
    de chat no PostgreSQL utilizando SQLAlchemy.
    """

    @staticmethod
    def buscar_por_id(db: Session, mensagem_id: int) -> Optional[Mensagem]:
        """
        Busca uma mensagem ativa no banco de dados pelo seu ID único.
        """
        return db.query(Mensagem).filter(
            Mensagem.id == mensagem_id,
            Mensagem.deletado == False
        ).first()

    @staticmethod
    def usuario_ocultou_mensagem(msg: Mensagem, usuario_id: int) -> bool:
        """
        Auxiliar que verifica se a mensagem foi ocultada pelo usuário específico
        através da coluna deletado_por (IDs separados por vírgula).
        """
        if msg.deletado:
            return True
        if not msg.deletadoPor:
            return False
        lista_deletados = [u.strip() for u in msg.deletadoPor.split(",") if u.strip()]
        return str(usuario_id) in lista_deletados

    @staticmethod
    def listar_mensagens_conversa(db: Session, conversa_id: int, usuario_id: int) -> List[Mensagem]:
        """
        Retorna todas as mensagens da conversa ordenadas por data de envio (mais antigas primeiro),
        filtrando as mensagens deletadas globalmente e as mensagens ocultadas pelo usuário autenticado.
        """
        mensagens = (
            db.query(Mensagem)
            .filter(
                Mensagem.idConversa == conversa_id,
                Mensagem.deletado == False
            )
            .order_by(Mensagem.dataEnvio.asc())
            .all()
        )
        return [msg for msg in mensagens if not MensagemRepository.usuario_ocultou_mensagem(msg, usuario_id)]

    @staticmethod
    def buscar_ultima_mensagem(db: Session, conversa_id: int, usuario_id: int) -> Optional[Mensagem]:
        """
        Retorna a mensagem mais recente da conversa visível para o usuário especificado.
        """
        mensagens = (
            db.query(Mensagem)
            .filter(
                Mensagem.idConversa == conversa_id,
                Mensagem.deletado == False
            )
            .order_by(Mensagem.dataEnvio.desc())
            .all()
        )
        for msg in mensagens:
            if not MensagemRepository.usuario_ocultou_mensagem(msg, usuario_id):
                return msg
        return None

    @staticmethod
    def criar_mensagem(db: Session, mensagem: Mensagem) -> Mensagem:
        """
        Insere uma nova mensagem no banco de dados e commita a transação.
        """
        db.add(mensagem)
        db.commit()
        db.refresh(mensagem)
        return mensagem

    @staticmethod
    def ocultar_mensagem_para_usuario(db: Session, mensagem: Mensagem, usuario_id: int, total_participantes: int = 2) -> Mensagem:
        """
        Adiciona o ID do usuário à lista deletado_por.
        Se todos os participantes ocultarem a mensagem, marca soft delete global (deletado = True).
        """
        str_uid = str(usuario_id)
        deletados = [u.strip() for u in (mensagem.deletadoPor or "").split(",") if u.strip()]

        if str_uid not in deletados:
            deletados.append(str_uid)

        mensagem.deletadoPor = ",".join(deletados)

        if len(deletados) >= total_participantes:
            mensagem.deletado = True
            mensagem.dataDelecao = func.now()

        db.commit()
        db.refresh(mensagem)
        return mensagem
