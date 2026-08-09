from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.usuario_model import Usuario
from app.schemas.usuario_schema import UsuarioCadastro, UsuarioLogin, UsuarioUpdateSchema, UsuarioSenhaSchema
from app.repositories.usuario_repository import UsuarioRepository
from app.core.security import criptografar_senha, verificar_senha, criar_token_acesso

class UsuarioService:
    """
    Serviço que implementa as regras de negócio para a entidade Usuario.

    Faz a ponte entre os controladores da API e os repositórios de dados,
    executando validações de exclusividade, criptografia de senha e emissão de tokens.
    """

    @staticmethod
    def cadastrar(db: Session, dados: UsuarioCadastro) -> Usuario:
        """
        Cadastra um novo usuário no banco de dados.

        Valida se o e-mail, CPF e nome de usuário já estão em uso (incluindo deletados),
        criptografa a senha e persiste o novo usuário no PostgreSQL.
        """
        # 1. Verificar se o e-mail já existe (incluindo deletados)
        usuario_existente_email = UsuarioRepository.buscar_por_email_geral(db, dados.email)
        if usuario_existente_email:
            if usuario_existente_email.deletado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já foi cadastrado anteriormente e está associado a uma conta deletada."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O e-mail informado já está cadastrado no sistema."
            )

        # 2. Verificar se o CPF já existe (incluindo deletados)
        usuario_existente_cpf = UsuarioRepository.buscar_por_cpf_geral(db, dados.cpf)
        if usuario_existente_cpf:
            if usuario_existente_cpf.deletado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este CPF já foi cadastrado anteriormente e está associado a uma conta deletada."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O CPF informado já está cadastrado no sistema."
            )

        # 3. Verificar se o nome já existe (incluindo deletados)
        usuario_existente_nome = UsuarioRepository.buscar_por_nome_geral(db, dados.nome)
        if usuario_existente_nome:
            if usuario_existente_nome.deletado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este nome de usuário já foi cadastrado anteriormente e está associado a uma conta deletada."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O nome informado já está cadastrado no sistema."
            )

        # 4. Criptografar a senha do usuário
        senha_criptografada = criptografar_senha(dados.senha)

        # 5. Criar objeto do modelo SQLAlchemy
        novo_usuario = Usuario(
            nome=dados.nome,
            email=dados.email,
            senha=senha_criptografada,  # Salva a senha hashada no campo 'senha'
            cpf=dados.cpf,
            telefone=dados.telefone,
            biografia=dados.biografia,
            portfolio=dados.portfolio,
            tipo_conta=dados.tipo_conta
        )

        # 6. Salvar no banco usando o repositório
        return UsuarioRepository.salvar(db, novo_usuario)

    @staticmethod
    def login(db: Session, dados: UsuarioLogin) -> dict:
        """
        Realiza a autenticação do usuário.

        Verifica se o e-mail existe, se a conta está ativa e se a senha fornecida bate com o hash.
        Se tudo estiver correto, emite um token JWT e retorna com os dados do usuário.
        """
        # 1. Buscar usuário pelo e-mail (incluindo deletados)
        usuario = UsuarioRepository.buscar_por_email_geral(db, dados.email)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # 2. Verificar se o usuário está deletado (soft delete)
        if usuario.deletado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta conta foi desativada (deletada) e não pode ser acessada."
            )

        # 3. Verificar se a senha confere
        if not verificar_senha(dados.senha, usuario.senha):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Senha incorreta."
            )

        # 4. Gerar o token JWT de acesso contendo o ID e e-mail
        token_data = {
            "sub": str(usuario.id),
            "email": usuario.email,
            "tipo_conta": usuario.tipo_conta
        }
        token_acesso = criar_token_acesso(dados=token_data)

        # 5. Retornar dados estruturados para o controller
        return {
            "access_token": token_acesso,
            "token_type": "bearer",
            "usuario": usuario
        }

    @staticmethod
    def atualizar_perfil(db: Session, usuario_id: int, dados: UsuarioUpdateSchema) -> Usuario:
        """
        Atualiza os dados do perfil do usuário autenticado.

        Apenas os campos informados na requisição serão atualizados.
        Campos ausentes no body permanecem inalterados no banco de dados.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (extraído do token JWT).
            dados: Schema com os campos a serem atualizados.

        Returns:
            O objeto Usuario atualizado.

        Raises:
            HTTPException 404: Se o usuário não for encontrado.
        """
        # 1. Buscar o usuário ativo pelo ID
        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # 2. Extrair apenas os campos que foram enviados na requisição
        campos_atualizados = dados.model_dump(exclude_unset=True)

        # 3. Se nenhum campo foi enviado, retornar o usuário sem alterações
        if not campos_atualizados:
            return usuario

        # 4. Aplicar cada campo informado ao objeto SQLAlchemy
        for campo, valor in campos_atualizados.items():
            setattr(usuario, campo, valor)

        # 5. Persistir as alterações via repositório
        return UsuarioRepository.atualizar_usuario(db, usuario)

    @staticmethod
    def alterar_senha(db: Session, usuario_id: int, dados: UsuarioSenhaSchema) -> dict:
        """
        Altera a senha do usuário autenticado.

        Valida a senha atual, verifica a confirmação da nova senha,
        criptografa com bcrypt e persiste no banco de dados.

        Args:
            db: Sessão ativa do SQLAlchemy.
            usuario_id: ID do usuário autenticado (extraído do token JWT).
            dados: Schema com senhaAtual, novaSenha e confirmacaoSenha.

        Returns:
            Dicionário com mensagem de sucesso.

        Raises:
            HTTPException 404: Se o usuário não for encontrado.
            HTTPException 400: Se a senha atual estiver incorreta.
        """
        # 1. Buscar o usuário ativo pelo ID
        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # 2. Verificar se a senha atual confere com o hash armazenado
        if not verificar_senha(dados.senhaAtual, usuario.senha):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A senha atual informada está incorreta."
            )

        # 3. Criptografar a nova senha com bcrypt
        nova_senha_hash = criptografar_senha(dados.novaSenha)

        # 4. Persistir a nova senha via repositório
        UsuarioRepository.alterar_senha(db, usuario, nova_senha_hash)

        return {"message": "Senha alterada com sucesso."}

