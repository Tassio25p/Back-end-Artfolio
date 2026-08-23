from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.usuario_model import Usuario

class UsuarioRepository:
    """
    Repositório de dados para a entidade Usuario.

    Esta classe encapsula todas as consultas e operações de persistência
    relacionadas aos usuários no PostgreSQL utilizando o SQLAlchemy.
    """

    @staticmethod
    def buscar_por_email(db: Session, email: Optional[str]) -> Optional[Usuario]:
        """
        Busca um usuário ativo no banco de dados através do e-mail.
        Ignora usuários que foram marcados como deletados logicamente.
        """
        if not email or not email.strip():
            return None
        return db.query(Usuario).filter(
            func.lower(Usuario.email) == email.strip().lower(), 
            Usuario.deletado == False
        ).first()

    @staticmethod
    def buscar_por_cpf(db: Session, cpf: Optional[str]) -> Optional[Usuario]:
        """
        Busca um usuário ativo no banco de dados através do CPF/CNPJ.
        Limpa pontuações e verifica tanto formato limpo quanto formatado.
        """
        if not cpf or not cpf.strip():
            return None
        cpf_limpo = "".join(filter(str.isdigit, cpf))
        if not cpf_limpo:
            return None

        doc_formatado = None
        if len(cpf_limpo) == 11:
            doc_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        elif len(cpf_limpo) == 14:
            doc_formatado = f"{cpf_limpo[:2]}.{cpf_limpo[2:5]}.{cpf_limpo[5:8]}/{cpf_limpo[8:12]}-{cpf_limpo[12:]}"

        return db.query(Usuario).filter(
            or_(
                Usuario.cpf_cnpj == cpf_limpo,
                Usuario.cpf_cnpj == doc_formatado
            ),
            Usuario.deletado == False
        ).first()

    @staticmethod
    def buscar_por_id(db: Session, usuario_id: int) -> Optional[Usuario]:
        """
        Busca um usuário ativo pelo seu ID único.
        """
        return db.query(Usuario).filter(
            Usuario.id == usuario_id, 
            Usuario.deletado == False
        ).first()

    @staticmethod
    def buscar_por_email_geral(db: Session, email: Optional[str]) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do e-mail,
        incluindo usuários que foram deletados logicamente.
        """
        if not email or not email.strip():
            return None
        return db.query(Usuario).filter(
            func.lower(Usuario.email) == email.strip().lower()
        ).first()

    @staticmethod
    def buscar_por_cpf_geral(db: Session, cpf: Optional[str]) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do CPF/CNPJ,
        incluindo usuários que foram deletados logicamente.
        Compara tanto formato apenas com dígitos quanto formato com pontuação.
        """
        if not cpf or not cpf.strip():
            return None
        cpf_limpo = "".join(filter(str.isdigit, cpf))
        if not cpf_limpo:
            return None

        doc_formatado = None
        if len(cpf_limpo) == 11:
            doc_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        elif len(cpf_limpo) == 14:
            doc_formatado = f"{cpf_limpo[:2]}.{cpf_limpo[2:5]}.{cpf_limpo[5:8]}/{cpf_limpo[8:12]}-{cpf_limpo[12:]}"

        return db.query(Usuario).filter(
            or_(
                Usuario.cpf_cnpj == cpf_limpo,
                Usuario.cpf_cnpj == doc_formatado
            )
        ).first()

    @staticmethod
    def buscar_por_nome_geral(db: Session, nome: Optional[str]) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do nome completo,
        incluindo usuários que foram deletados logicamente.
        """
        if not nome or not nome.strip():
            return None
        return db.query(Usuario).filter(
            func.lower(Usuario.nome) == nome.strip().lower()
        ).first()

    @staticmethod
    def salvar(db: Session, usuario: Usuario) -> Usuario:
        """
        Salva um objeto Usuario no banco de dados PostgreSQL.

        Executa o insert/update, commita a transação e atualiza o objeto
        para conter os valores gerados pelo banco (como ID e data de criação).
        """
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def atualizar_usuario(db: Session, usuario: Usuario) -> Usuario:
        """
        Persiste as alterações de um usuário existente no banco de dados.

        Commita a transação e faz refresh para garantir que o objeto
        reflita os valores mais recentes do PostgreSQL.
        """
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def alterar_senha(db: Session, usuario: Usuario, nova_senha_hash: str) -> Usuario:
        """
        Atualiza a senha hashada de um usuário existente no banco de dados.

        Recebe a nova senha já criptografada com bcrypt e persiste a alteração.
        """
        usuario.senha = nova_senha_hash
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def listar_artistas(db: Session, busca: Optional[str] = None) -> List[Usuario]:
        """
        Retorna a lista de usuários/artistas ativos (deletado == False).
        Aplica filtro de busca case-insensitive por nome ou biografia se informado.
        """
        query = db.query(Usuario).filter(Usuario.deletado == False)
        if busca and busca.strip():
            termo = f"%{busca.strip()}%"
            query = query.filter(
                or_(
                    Usuario.nome.ilike(termo),
                    Usuario.biografia.ilike(termo)
                )
            )
        return query.order_by(Usuario.nome.asc()).all()

