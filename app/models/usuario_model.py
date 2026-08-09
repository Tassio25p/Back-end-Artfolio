from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from app.database import Base

class Usuario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'usuario' no PostgreSQL.

    Este modelo mapeia diretamente os campos e tipos definidos no script SQL,
    incluindo as colunas de deleção lógica (soft delete) e os campos em camelCase.
    Além disso, adiciona o campo 'tipo_conta' para controle de permissões.
    
    NOTA: Caso você já tenha rodado o script SQL inicial sem a coluna 'tipo_conta',
    será necessário executar o seguinte comando no seu banco de dados:
    ALTER TABLE Usuario ADD COLUMN tipo_conta VARCHAR(20) NOT NULL DEFAULT 'cliente';
    """
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)  # Armazenará o hash da senha gerado pelo bcrypt
    cpf = Column(String(14), unique=True, nullable=False, index=True)
    telefone = Column(String(20), nullable=True)
    biografia = Column(Text, nullable=True)
    fotoPerfil = Column("fotoperfil", String(255), nullable=True)
    dataCriacao = Column("datacriacao", DateTime, server_default=func.now())
    portfolio = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    behance = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    deletado = Column(Boolean, default=False)
    dataDelecao = Column("datadelecao", DateTime, nullable=True)
    
    # Campo adicionado para atender os requisitos de tipo de conta (cliente, artista, moderador, admin)
    tipo_conta = Column("tipo_conta", String(20), nullable=False, default="cliente")

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome}', email='{self.email}', tipo_conta='{self.tipo_conta}')>"
