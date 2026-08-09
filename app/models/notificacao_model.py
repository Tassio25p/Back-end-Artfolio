from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Notificacao(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'notificacao' no PostgreSQL.

    Armazena as notificações enviadas aos usuários sobre interações
    como curtidas, comentários, seguidores e mensagens.
    Utiliza soft delete seguindo o padrão do projeto.
    """
    __tablename__ = "notificacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idUsuario = Column("idusuario", Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # 'LIKE', 'FOLLOW', 'COMMENT', 'MESSAGE'
    titulo = Column(String(100), nullable=False)
    mensagem = Column(Text, nullable=False)
    idRemetente = Column("idremetente", Integer, ForeignKey("usuario.id"), nullable=True)
    idPostagem = Column("idpostagem", Integer, ForeignKey("postagem.id"), nullable=True)
    idComentario = Column("idcomentario", Integer, ForeignKey("comentario.id"), nullable=True)
    idConversa = Column("idconversa", Integer, ForeignKey("conversa.id"), nullable=True)
    lida = Column(Boolean, default=False)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)

    # Relacionamentos para carregar dados do destinatário, remetente e postagem
    usuario = relationship("Usuario", foreign_keys=[idUsuario], lazy="joined")
    remetente = relationship("Usuario", foreign_keys=[idRemetente], lazy="joined")
    postagem = relationship("Postagem", foreign_keys=[idPostagem], lazy="joined")

    def __repr__(self):
        return f"<Notificacao(id={self.id}, idUsuario={self.idUsuario}, tipo='{self.tipo}', lida={self.lida})>"
