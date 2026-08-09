from typing import Optional
from sqlalchemy.orm import Session
from app.models.usuario_model import Usuario

class UsuarioRepository:
    """
    Repositório de dados para a entidade Usuario.

    Esta classe encapsula todas as consultas e operações de persistência
    relacionadas aos usuários no PostgreSQL utilizando o SQLAlchemy.
    """

    @staticmethod
    def buscar_por_email(db: Session, email: str) -> Optional[Usuario]:
        """
        Busca um usuário ativo no banco de dados através do e-mail.

        Ignora usuários que foram marcados como deletados logicamente.
        """
        return db.query(Usuario).filter(
            Usuario.email == email, 
            Usuario.deletado == False
        ).first()

    @staticmethod
    def buscar_por_cpf(db: Session, cpf: str) -> Optional[Usuario]:
        """
        Busca um usuário ativo no banco de dados através do CPF.

        Útil para garantir a unicidade do CPF durante o cadastro.
        """
        return db.query(Usuario).filter(
            Usuario.cpf == cpf, 
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
    def buscar_por_email_geral(db: Session, email: str) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do e-mail,
        incluindo usuários que foram deletados logicamente.
        """
        return db.query(Usuario).filter(Usuario.email == email).first()

    @staticmethod
    def buscar_por_cpf_geral(db: Session, cpf: str) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do CPF,
        incluindo usuários que foram deletados logicamente.
        """
        return db.query(Usuario).filter(Usuario.cpf == cpf).first()

    @staticmethod
    def buscar_por_nome_geral(db: Session, nome: str) -> Optional[Usuario]:
        """
        Busca um usuário no banco de dados através do nome completo,
        incluindo usuários que foram deletados logicamente.
        """
        return db.query(Usuario).filter(Usuario.nome == nome).first()

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
