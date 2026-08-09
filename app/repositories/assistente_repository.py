from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.assistente_conversa_model import AssistenteConversa
from app.models.assistente_mensagem_model import AssistenteMensagem


class AssistenteRepository:
    """
    Repositório de dados para as entidades AssistenteConversa e AssistenteMensagem.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    # --- Conversa ---

    @staticmethod
    def criar_conversa(db: Session, id_usuario: int, titulo: Optional[str] = None) -> AssistenteConversa:
        """
        Cria uma nova conversa do assistente para o usuário.
        """
        conversa = AssistenteConversa(
            idUsuario=id_usuario,
            titulo=titulo,
        )
        db.add(conversa)
        db.commit()
        db.refresh(conversa)
        return conversa

    @staticmethod
    def buscar_conversa_por_id(db: Session, conversa_id: int) -> Optional[AssistenteConversa]:
        """
        Busca uma conversa ativa (não deletada) pelo seu ID.
        """
        return db.query(AssistenteConversa).filter(
            AssistenteConversa.id == conversa_id,
            AssistenteConversa.deletado == False
        ).first()

    @staticmethod
    def listar_conversas(db: Session, id_usuario: int) -> List[AssistenteConversa]:
        """
        Lista todas as conversas ativas (não deletadas) de um usuário,
        ordenadas pela data de atualização mais recente.
        """
        return db.query(AssistenteConversa).filter(
            AssistenteConversa.idUsuario == id_usuario,
            AssistenteConversa.deletado == False
        ).order_by(AssistenteConversa.dataAtualizacao.desc()).all()

    @staticmethod
    def atualizar_conversa(db: Session, conversa: AssistenteConversa) -> AssistenteConversa:
        """
        Salva as alterações de uma conversa existente.
        """
        db.commit()
        db.refresh(conversa)
        return conversa

    @staticmethod
    def encerrar_conversa(db: Session, conversa: AssistenteConversa) -> AssistenteConversa:
        """
        Marca uma conversa como inativa (encerrada).
        """
        conversa.ativa = False
        db.commit()
        db.refresh(conversa)
        return conversa

    @staticmethod
    def deletar_conversa(db: Session, conversa: AssistenteConversa) -> None:
        """
        Realiza o soft delete de uma conversa.
        """
        conversa.deletado = True
        conversa.dataDelecao = datetime.utcnow()
        db.commit()

    # --- Mensagem ---

    @staticmethod
    def criar_mensagem(
        db: Session,
        id_conversa: int,
        remetente: str,
        mensagem: str,
        ferramenta_usada: Optional[str] = None,
        resposta_json: Optional[dict] = None
    ) -> AssistenteMensagem:
        """
        Cria e persiste uma nova mensagem dentro de uma conversa do assistente.
        """
        msg = AssistenteMensagem(
            idConversa=id_conversa,
            remetente=remetente,
            mensagem=mensagem,
            ferramentaUsada=ferramenta_usada,
            respostaJson=resposta_json,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def listar_mensagens(db: Session, id_conversa: int) -> List[AssistenteMensagem]:
        """
        Lista todas as mensagens não deletadas de uma conversa,
        ordenadas pela data de envio.
        """
        return db.query(AssistenteMensagem).filter(
            AssistenteMensagem.idConversa == id_conversa,
            AssistenteMensagem.deletado == False
        ).order_by(AssistenteMensagem.dataEnvio.asc()).all()
