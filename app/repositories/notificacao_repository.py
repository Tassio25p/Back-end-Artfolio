from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.notificacao_model import Notificacao


class NotificacaoRepository:
    """
    Repositório de dados para a entidade Notificacao.
    Encapsula consultas SQL/SQLAlchemy no PostgreSQL.
    """

    @staticmethod
    def criar(db: Session, notificacao: Notificacao) -> Notificacao:
        """
        Persiste uma nova notificação no banco de dados.
        """
        db.add(notificacao)
        db.commit()
        db.refresh(notificacao)
        return notificacao

    @staticmethod
    def buscar_por_id(db: Session, notificacao_id: int) -> Optional[Notificacao]:
        """
        Busca uma notificação ativa pelo seu ID.
        """
        return db.query(Notificacao).filter(
            Notificacao.id == notificacao_id,
            Notificacao.deletado == False
        ).first()

    @staticmethod
    def listar_por_usuario(db: Session, usuario_id: int) -> List[Notificacao]:
        """
        Lista todas as notificações ativas de um usuário, ordenadas por data desc (mais recentes primeiro).
        """
        return db.query(Notificacao).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.deletado == False
        ).order_by(Notificacao.dataCriacao.desc()).all()

    @staticmethod
    def listar_com_filtros(
        db: Session,
        usuario_id: int,
        tipo: Optional[str] = None,
        apenas_nao_lidas: bool = False,
        limite: int = 20,
        offset: int = 0
    ) -> tuple:
        """
        Retorna (itens_paginados, total_filtrado, total_nao_lidas_do_usuario).
        """
        total_nao_lidas = db.query(func.count(Notificacao.id)).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.lida == False,
            Notificacao.deletado == False
        ).scalar() or 0

        query = db.query(Notificacao).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.deletado == False
        )

        if apenas_nao_lidas:
            query = query.filter(Notificacao.lida == False)

        if tipo:
            t = tipo.strip().lower()
            if t not in ("", "todas", "all"):
                mapa_tipos = {
                    "mensagem": ["mensagem", "message"],
                    "curtida": ["curtida", "like"],
                    "comentario": ["comentario", "comment"],
                    "seguidor": ["seguidor", "follow"],
                    "proposta": ["proposta", "proposal"],
                    "sistema": ["sistema", "system"],
                    "interacao": ["curtida", "comentario", "seguidor", "like", "comment", "follow"],
                }
                if t in mapa_tipos:
                    tipos_aceitos = mapa_tipos[t]
                    query = query.filter(func.lower(Notificacao.tipo).in_(tipos_aceitos))
                else:
                    query = query.filter(func.lower(Notificacao.tipo) == t)

        total_filtrado = query.count()
        itens = query.order_by(Notificacao.dataCriacao.desc()).offset(offset).limit(limite).all()

        return itens, total_filtrado, total_nao_lidas

    @staticmethod
    def contar_nao_lidas(db: Session, usuario_id: int) -> int:
        """
        Conta a quantidade de notificações não lidas e não deletadas de um usuário.
        """
        return db.query(func.count(Notificacao.id)).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.lida == False,
            Notificacao.deletado == False
        ).scalar() or 0

    @staticmethod
    def marcar_como_lida(db: Session, notificacao: Notificacao) -> Notificacao:
        """
        Marca uma notificação como lida.
        """
        notificacao.lida = True
        db.commit()
        db.refresh(notificacao)
        return notificacao

    @staticmethod
    def marcar_todas_como_lidas(db: Session, usuario_id: int) -> int:
        """
        Marca todas as notificações ativas não lidas de um usuário como lidas.
        Retorna a quantidade de notificações atualizadas.
        """
        qtd = db.query(Notificacao).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.lida == False,
            Notificacao.deletado == False
        ).update({"lida": True}, synchronize_session=False)
        db.commit()
        return qtd

    @staticmethod
    def deletar(db: Session, notificacao: Notificacao) -> None:
        """
        Realiza o soft delete de uma notificação.
        """
        notificacao.deletado = True
        notificacao.dataDelecao = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def deletar_todas(db: Session, usuario_id: int) -> int:
        """
        Realiza o soft delete de todas as notificações de um usuário.
        """
        qtd = db.query(Notificacao).filter(
            Notificacao.idUsuario == usuario_id,
            Notificacao.deletado == False
        ).update({
            "deletado": True,
            "dataDelecao": datetime.now(timezone.utc)
        }, synchronize_session=False)
        db.commit()
        return qtd
