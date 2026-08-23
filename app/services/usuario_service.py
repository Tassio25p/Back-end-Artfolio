import json
import os
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.models.usuario_model import Usuario
from app.schemas.usuario_schema import UsuarioCadastro, UsuarioLogin, UsuarioUpdateSchema, UsuarioSenhaSchema, UsuarioResposta, PerfilPublicoResposta
from app.schemas.seguidor_schema import RelacionamentoStatusResposta
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.seguidor_repository import SeguidorRepository
from app.repositories.postagem_repository import PostagemRepository
from app.services.seguidor_service import SeguidorService
from app.core.security import criptografar_senha, verificar_senha, criar_token_acesso
from app.core.config import settings
from app.services.media_service import MediaService
from app.redis_client import redis_client

# Tipos MIME permitidos para foto de perfil
MIME_TYPES_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Tamanho máximo da foto de perfil: 5 MB
TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024

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

        # 3. Verificar se a conta foi criada via Google sem senha
        if not usuario.senha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta conta foi criada com o Google. Por favor, acesse utilizando o botão do Google."
            )

        # 4. Verificar se a senha confere
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
    def login_google(db: Session, token: str) -> dict:
        """
        Valida o ID token retornado pelo Google, cadastra o usuário se não existir e emite JWT.
        """
        import requests
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        id_info = None
        google_client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID")
        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=google_client_id if google_client_id else None
            )
        except Exception:
            try:
                resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}", timeout=10)
                if resp.status_code == 200:
                    id_info = resp.json()
            except Exception:
                pass

        if not id_info or not id_info.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token do Google inválido ou expirado."
            )

        email = id_info.get("email").lower()
        nome = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]
        foto_perfil = id_info.get("picture")

        usuario = UsuarioRepository.buscar_por_email_geral(db, email)
        if usuario:
            if usuario.deletado:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Esta conta foi desativada (deletada) e não pode ser acessada."
                )
            if not usuario.fotoPerfil and foto_perfil:
                usuario.fotoPerfil = foto_perfil
                UsuarioRepository.salvar(db, usuario)
        else:
            novo_usuario = Usuario(
                nome=nome,
                email=email,
                senha=None,
                fotoPerfil=foto_perfil,
                tipo_conta="artista"
            )
            usuario = UsuarioRepository.salvar(db, novo_usuario)

        token_data = {
            "sub": str(usuario.id),
            "email": usuario.email,
            "tipo_conta": usuario.tipo_conta
        }
        token_acesso = criar_token_acesso(dados=token_data)

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
        usuario_atualizado = UsuarioRepository.atualizar_usuario(db, usuario)

        # 6. Invalidar cache do perfil e obras
        redis_client.delete(f"artfolio:perfil:{usuario_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        return usuario_atualizado

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

    @staticmethod
    def atualizar_foto_perfil(db: Session, usuario_id: int, arquivo: UploadFile) -> Usuario:
        """
        Valida, realiza upload no Cloudinary e vincula uma nova foto de perfil ao usuário autenticado.
        """
        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # 1. Upload seguro para o Cloudinary (pasta 'artfolio/perfis', máx. 5MB)
        secure_url = MediaService.upload_imagem(arquivo, folder="artfolio/perfis", max_size_mb=5)

        # 2. Atualizar URL no banco de dados
        usuario.fotoPerfil = secure_url
        usuario_atualizado = UsuarioRepository.atualizar_usuario(db, usuario)

        # 3. Invalidar cache
        redis_client.delete(f"artfolio:perfil:{usuario_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        return usuario_atualizado

    @staticmethod
    def remover_foto_perfil(db: Session, usuario_id: int) -> Usuario:
        """
        Remove a foto de perfil do usuário e exclui o arquivo local caso exista.
        """
        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        if usuario.fotoPerfil and usuario.fotoPerfil.startswith("/uploads/perfis/"):
            foto_nome = os.path.basename(usuario.fotoPerfil)
            caminho_foto = os.path.join(settings.UPLOAD_DIR, "perfis", foto_nome)
            if os.path.exists(caminho_foto):
                try:
                    os.remove(caminho_foto)
                except Exception:
                    pass

        usuario.fotoPerfil = None
        usuario_atualizado = UsuarioRepository.atualizar_usuario(db, usuario)

        # Invalidar cache
        redis_client.delete(f"artfolio:perfil:{usuario_id}")
        redis_client.delete_pattern("artfolio:obras:*")

        return usuario_atualizado

    @staticmethod
    def buscar_perfil_com_cache(db: Session, usuario_id: int) -> Optional[UsuarioResposta]:
        """
        Busca o perfil público do usuário com suporte a cache Redis (artfolio:perfil:{usuario_id}).
        """
        cache_key = f"artfolio:perfil:{usuario_id}"
        val_cache = redis_client.get(cache_key)
        if val_cache:
            try:
                dados_json = json.loads(val_cache)
                return UsuarioResposta.model_validate(dados_json)
            except Exception:
                pass

        usuario = UsuarioRepository.buscar_por_id(db, usuario_id)
        if not usuario:
            return None

        try:
            dados_dict = UsuarioResposta.model_validate(usuario).model_dump(mode="json")
            redis_client.set(cache_key, json.dumps(dados_dict), expira_segundos=300)
        except Exception:
            pass

        return UsuarioResposta.model_validate(usuario)

    @staticmethod
    def obter_perfil_publico(db: Session, target_id: int, me_id: Optional[int] = None) -> PerfilPublicoResposta:
        """
        Retorna as informações públicas detalhadas de um usuário,
        incluindo contagem real de seguidores, seguindo, obras e status de relacionamento com o solicitante.
        """
        usuario = UsuarioRepository.buscar_por_id(db, target_id)
        if not usuario or usuario.deletado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        seguidores_cnt = SeguidorRepository.contar_seguidores(db, target_id)
        seguindo_cnt = SeguidorRepository.contar_seguindo(db, target_id)
        
        obras = PostagemRepository.listar_todas(db, usuario_id=target_id)
        obras_cnt = len(obras)

        if me_id:
            rel_status = SeguidorService.obter_status_relacionamento(db, me_id, target_id)
        else:
            rel_status = RelacionamentoStatusResposta(
                seguidoresCount=seguidores_cnt,
                seguindoCount=seguindo_cnt
            )

        return PerfilPublicoResposta(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            telefone=usuario.telefone,
            biografia=usuario.biografia,
            fotoPerfil=usuario.fotoPerfil,
            portfolio=usuario.portfolio,
            instagram=usuario.instagram,
            behance=usuario.behance,
            website=usuario.website,
            tipo_conta=usuario.tipo_conta,
            dataCriacao=usuario.dataCriacao,
            seguidoresCount=seguidores_cnt,
            seguindoCount=seguindo_cnt,
            obrasCount=obras_cnt,
            relacionamento=rel_status
        )

    @staticmethod
    def listar_artistas(db: Session, busca: Optional[str] = None) -> List[PerfilPublicoResposta]:
        """
        Retorna a lista de perfis públicos de todos os artistas/usuários cadastrados ativos,
        aplicando o filtro de busca caso informado.
        """
        artistas = UsuarioRepository.listar_artistas(db, busca=busca)
        resultado = []
        for artista in artistas:
            perfil = UsuarioService.obter_perfil_publico(db, target_id=artista.id)
            resultado.append(perfil)
        return resultado




