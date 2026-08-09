import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.postagem_model import Postagem
from app.repositories.postagem_repository import PostagemRepository
from app.schemas.postagem_schema import PostagemCriar, PostagemAtualizar, PostagemResposta
from app.redis_client import redis_client

class PostagemService:
    """
    Serviço contendo as regras de negócio relacionadas às Obras (Postagens).
    Utiliza o SafeRedisClient para caching (TTL 300s) e invalidação automática.
    """

    @staticmethod
    def listar_obras(
        db: Session,
        usuario_id: Optional[int] = None,
        categoria_id: Optional[int] = None
    ) -> List:
        """
        Retorna a lista de obras ativas no sistema, aplicando os filtros caso fornecidos.
        Utiliza cache Redis (artfolio:obras:*) com fallback transparente para o PostgreSQL.
        """
        cache_key = f"artfolio:obras:user_{usuario_id or 'all'}_cat_{categoria_id or 'all'}"

        # 1. Buscar do cache Redis
        val_cache = redis_client.get(cache_key)
        if val_cache:
            try:
                dados_json = json.loads(val_cache)
                return [PostagemResposta.model_validate(item) for item in dados_json]
            except Exception:
                pass

        # 2. Buscar no PostgreSQL (fonte oficial)
        obras = PostagemRepository.listar_todas(db, usuario_id=usuario_id, categoria_id=categoria_id)

        # 3. Salvar no Redis com expiração de 300 segundos (5 minutos)
        try:
            dados_dict = [PostagemResposta.model_validate(o).model_dump(mode="json") for o in obras]
            redis_client.set(cache_key, json.dumps(dados_dict), expira_segundos=300)
        except Exception:
            pass

        return obras

    @staticmethod
    def buscar_obra_por_id(db: Session, postagem_id: int) -> Postagem:
        """
        Busca uma obra pelo ID com cache Redis. Lança exceção HTTP 404 se não encontrada.
        """
        cache_key = f"artfolio:obras:id:{postagem_id}"

        # 1. Buscar do cache Redis
        val_cache = redis_client.get(cache_key)
        if val_cache:
            try:
                dados_json = json.loads(val_cache)
                return PostagemResposta.model_validate(dados_json)
            except Exception:
                pass

        # 2. Buscar no PostgreSQL (fonte oficial)
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        # 3. Salvar no Redis com expiração de 300 segundos
        try:
            dados_dict = PostagemResposta.model_validate(obra).model_dump(mode="json")
            redis_client.set(cache_key, json.dumps(dados_dict), expira_segundos=300)
        except Exception:
            pass

        return obra

    @staticmethod
    def criar_postagem(db: Session, usuario_id: int, dados: PostagemCriar) -> Postagem:
        """
        Cria e persiste uma nova postagem no banco de dados.
        Invalida o cache de obras no Redis.
        """
        nova_postagem = Postagem(
            idUsuario=usuario_id,
            idCategoria=dados.idCategoria,
            legenda=dados.legenda,
            arquivoUrl=dados.arquivoUrl,
        )
        postagem_criada = PostagemRepository.criar(db, nova_postagem)

        # Invalida o cache de obras
        redis_client.delete_pattern("artfolio:obras:*")

        return postagem_criada

    @staticmethod
    def atualizar_postagem(db: Session, postagem_id: int, usuario_id: int, dados: PostagemAtualizar) -> Postagem:
        """
        Atualiza os campos informados de uma postagem existente.
        Invalida o cache de obras no Redis.
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        if obra.idUsuario != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta postagem."
            )

        if dados.idCategoria is not None:
            obra.idCategoria = dados.idCategoria
        if dados.legenda is not None:
            obra.legenda = dados.legenda
        if dados.arquivoUrl is not None:
            obra.arquivoUrl = dados.arquivoUrl

        postagem_atualizada = PostagemRepository.atualizar(db, obra)

        # Invalida o cache de obras
        redis_client.delete_pattern("artfolio:obras:*")

        return postagem_atualizada

    @staticmethod
    def deletar_postagem(db: Session, postagem_id: int, usuario_id: int, tipo_conta: str = "cliente") -> None:
        """
        Realiza o soft delete de uma postagem e invalida o cache no Redis.
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        tipos_admin = ["admin", "moderador"]
        if obra.idUsuario != usuario_id and tipo_conta not in tipos_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para excluir esta postagem."
            )

        PostagemRepository.deletar(db, obra)

        # Invalida o cache de obras
        redis_client.delete_pattern("artfolio:obras:*")

