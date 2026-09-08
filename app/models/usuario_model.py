from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, synonym
from app.database import Base

class Usuario(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'usuario' no PostgreSQL.
    Mapeia todos os campos definidos no schema do banco de dados,
    incluindo autoidentificação de Pessoa Física/Jurídica (PF/PJ),
    aceite dos termos de uso, soft delete e dados dinâmicos de portfólio.
    """
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    senha: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Hash gerado pelo bcrypt ou None para login com Google
    tipo_usuario: Mapped[str] = mapped_column("tipo_usuario", String(20), nullable=False, default="PF")  # 'PF' ou 'PJ'
    cpf_cnpj: Mapped[Optional[str]] = mapped_column("cpf_cnpj", String(18), unique=True, nullable=True, index=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    biografia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fotoPerfil: Mapped[Optional[str]] = mapped_column("fotoperfil", String(255), nullable=True)
    portfolio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Redes sociais opcionais
    instagram: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    behance: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Campos de Portfólio Dinâmico e Currículo Artístico
    trajetoria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    especializacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    certificados: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON stringificado com certificados/documentos
    
    # Conformidade legal e Termos de Uso
    termoAceito: Mapped[bool] = mapped_column("termoaceito", Boolean, nullable=False, default=False)
    dataAceiteTermo: Mapped[Optional[datetime]] = mapped_column("dataaceitetermo", DateTime, nullable=True)
    versaoTermo: Mapped[Optional[str]] = mapped_column("versaotermo", String(10), nullable=True)

    # Auditoria e Soft delete
    dataCriacao: Mapped[Optional[datetime]] = mapped_column("datacriacao", DateTime, server_default=func.now())
    deletado: Mapped[bool] = mapped_column(Boolean, default=False)
    dataDelecao: Mapped[Optional[datetime]] = mapped_column("datadelecao", DateTime, nullable=True)
    
    # Papel da conta e configurações de plano/personalização
    tipo_conta: Mapped[str] = mapped_column("tipo_conta", String(20), nullable=False, default="artista")
    mostrar_moldura_led: Mapped[bool] = mapped_column("mostrar_moldura_led", Boolean, default=True)
    mensagem_cta: Mapped[Optional[str]] = mapped_column("mensagem_cta", Text, nullable=True)

    # Status de conta e moderação
    ativo: Mapped[bool] = mapped_column("ativo", Boolean, nullable=False, default=True)
    suspenso_ate: Mapped[Optional[datetime]] = mapped_column("suspenso_ate", DateTime, nullable=True)

    # Sinônimos para compatibilidade
    cpf = synonym("cpf_cnpj")
    papel = synonym("tipo_conta")

    def __repr__(self) -> str:
        return f"<Usuario(id={self.id}, nome='{self.nome}', email='{self.email}', tipo_usuario='{self.tipo_usuario}')>"
