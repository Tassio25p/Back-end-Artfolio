import json
from datetime import datetime, timezone
from typing import List, Optional, Union, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.postagem_model import Postagem
from app.models.categoria_model import Categoria
from app.repositories.postagem_repository import PostagemRepository
from app.repositories.curtida_repository import CurtidaRepository
from app.repositories.comentario_repository import ComentarioRepository
from app.repositories.obra_salva_repository import ObraSalvaRepository
from app.repositories.seguidor_repository import SeguidorRepository
from app.models.postagem_visualizacao_model import PostagemVisualizacao
from app.schemas.postagem_schema import PostagemCriar, PostagemAtualizar, PostagemResposta
from app.services.plano_service import PlanoService
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
        categoria_id: Optional[int] = None,
        termo_busca: Optional[str] = None,
        usuario_atual_id: Optional[int] = None
    ) -> List[Union[Postagem, PostagemResposta]]:
        """
        Retorna a lista de obras ativas no sistema, aplicando os filtros caso fornecidos.
        Utiliza cache Redis (artfolio:obras:*) com fallback transparente para o PostgreSQL.
        """
        cache_key = f"artfolio:obras:user_{usuario_id or 'all'}_cat_{categoria_id or 'all'}_busca_{termo_busca or 'none'}_me_{usuario_atual_id or 'anon'}"

        # 1. Buscar do cache Redis
        val_cache = redis_client.get(cache_key)
        if val_cache:
            try:
                dados_json = json.loads(val_cache)
                return [PostagemResposta.model_validate(item) for item in dados_json]
            except Exception:
                pass

        # 2. Buscar no PostgreSQL (fonte oficial)
        obras = PostagemRepository.listar_todas(
            db,
            usuario_id=usuario_id,
            categoria_id=categoria_id,
            termo_busca=termo_busca
        )

        # Enriquecer cada obra com contagens de likes, comentários, salvos e status de interação
        obras_enriquecidas = []
        planos_cache = {}
        for o in obras:
            total_likes = CurtidaRepository.contar_por_postagem(db, o.id)
            total_comentarios = ComentarioRepository.contar_por_postagem(db, o.id)
            total_salvos = ObraSalvaRepository.contar_por_postagem(db, o.id)
            curtido = CurtidaRepository.buscar(db, usuario_atual_id, o.id) is not None if usuario_atual_id else False
            salvo = ObraSalvaRepository.buscar(db, usuario_atual_id, o.id) is not None if usuario_atual_id else False

            o.totalCurtidas = total_likes
            o.totalComentarios = total_comentarios
            o.totalSalvos = total_salvos
            o.curtido_por_mim = curtido
            o.salvo_por_mim = salvo

            if o.usuario:
                if o.usuario.id not in planos_cache:
                    planos_cache[o.usuario.id] = PlanoService.obter_tipo_plano_usuario(db, o.usuario.id)
                o.usuario.plano = planos_cache[o.usuario.id]

            obras_enriquecidas.append(o)

        # 3. Salvar no Redis com expiração de 300 segundos (5 minutos)
        try:
            dados_dict = [PostagemResposta.model_validate(o).model_dump(mode="json") for o in obras_enriquecidas]
            redis_client.set(cache_key, json.dumps(dados_dict), expira_segundos=300)
        except Exception:
            pass

        return obras_enriquecidas

    @staticmethod
    def buscar_obra_por_id(
        db: Session,
        postagem_id: int,
        usuario_atual_id: Optional[int] = None,
        client_ip: Optional[str] = None
    ) -> Postagem:
        """
        Busca uma obra pelo ID, computa métricas em tempo real e incrementa visualizações únicas.
        Lança exceção HTTP 404 se não encontrada.
        """
        obra = PostagemRepository.buscar_por_id(db, postagem_id)
        if not obra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra não encontrada."
            )

        # 1. Registro de visualização única anti-farm
        nova_visualizacao = False
        if usuario_atual_id:
            # Usuário autenticado: busca se já registrou visualização
            ja_viu = db.query(PostagemVisualizacao).filter(
                PostagemVisualizacao.idPostagem == postagem_id,
                PostagemVisualizacao.idUsuario == usuario_atual_id
            ).first()
            if not ja_viu:
                try:
                    db.add(PostagemVisualizacao(idPostagem=postagem_id, idUsuario=usuario_atual_id))
                    nova_visualizacao = True
                except Exception:
                    db.rollback()
        else:
            # Usuário anônimo: controle por IP via Redis (expiração 24h)
            ip_val = client_ip or "anon"
            view_key = f"artfolio:view:{postagem_id}:{ip_val}"
            if not redis_client.get(view_key):
                redis_client.set(view_key, "1", expira_segundos=86400)
                nova_visualizacao = True

        if nova_visualizacao:
            try:
                obra.visualizacoes = (obra.visualizacoes or 0) + 1
                db.commit()
                db.refresh(obra)
            except Exception:
                db.rollback()

        # 2. Total de visualizações
        try:
            total_views_db = db.query(PostagemVisualizacao).filter(
                PostagemVisualizacao.idPostagem == postagem_id
            ).count()
            total_visualizacoes = max(obra.visualizacoes or 0, total_views_db)
        except Exception:
            total_visualizacoes = obra.visualizacoes or 0

        obra.visualizacoes = total_visualizacoes
        obra.total_visualizacoes = total_visualizacoes

        # 3. Métricas de engajamento em tempo real
        obra.totalCurtidas = CurtidaRepository.contar_por_postagem(db, obra.id)
        obra.total_curtidas = obra.totalCurtidas
        obra.totalComentarios = ComentarioRepository.contar_por_postagem(db, obra.id)
        obra.total_comentarios = obra.totalComentarios
        obra.totalSalvos = ObraSalvaRepository.contar_por_postagem(db, obra.id)
        obra.total_salvos = obra.totalSalvos

        obra.curtido_por_mim = CurtidaRepository.buscar(db, usuario_atual_id, obra.id) is not None if usuario_atual_id else False
        obra.usuario_curtiu = obra.curtido_por_mim
        obra.salvo_por_mim = ObraSalvaRepository.buscar(db, usuario_atual_id, obra.id) is not None if usuario_atual_id else False
        obra.usuario_salvou = obra.salvo_por_mim

        # Metadados complementares
        obra.titulo = obra.legenda or f"Obra #{obra.id}"
        obra.descricao = obra.legenda or ""
        obra.imagem_url = obra.arquivoUrl
        obra.data_criacao = obra.dataPostagem

        # 4. Dados do Autor / Usuário enriquecidos com seguidores e plano
        if obra.usuario:
            plano_usuario = PlanoService.obter_tipo_plano_usuario(db, obra.usuario.id)
            total_seguidores = SeguidorRepository.contar_seguidores(db, obra.usuario.id)
            usuario_seguindo = SeguidorRepository.buscar(db, usuario_atual_id, obra.usuario.id) is not None if usuario_atual_id else False

            obra.usuario.plano = plano_usuario
            obra.usuario.total_seguidores = total_seguidores
            obra.usuario.seguidores = total_seguidores
            obra.usuario.usuario_seguindo = usuario_seguindo
            obra.usuario.seguindo_usuario = usuario_seguindo
            obra.usuario.foto_perfil = obra.usuario.fotoPerfil

            # Objeto autor compatível com PostagemUsuarioResumidoResposta
            obra.autor = obra.usuario

        return obra

    @staticmethod
    def criar_postagem(db: Session, usuario_id: int, dados: PostagemCriar) -> Postagem:
        """
        Cria e persiste uma nova postagem no banco de dados.
        Associa categorias via tabela associativa postagem_categoria.
        Invalida o cache de obras no Redis.
        """
        categoria_ids: List[int] = []
        if dados.idCategorias:
            categoria_ids.extend(dados.idCategorias)
        if dados.idCategoria and dados.idCategoria not in categoria_ids:
            categoria_ids.append(dados.idCategoria)
        if dados.nomesCategorias:
            for cat_nome in dados.nomesCategorias:
                if cat_nome and cat_nome.strip():
                    nome_limpo = cat_nome.strip()
                    cat = db.query(Categoria).filter(
                        func.lower(Categoria.nomeCategoria) == nome_limpo.lower(),
                        Categoria.deletado == False
                    ).first()
                    if not cat:
                        cat = Categoria(nomeCategoria=nome_limpo)
                        db.add(cat)
                        db.flush()
                    if cat and cat.id not in categoria_ids:
                        categoria_ids.append(cat.id)

        from app.services.plano_service import PlanoService
        plano_tipo = PlanoService.obter_tipo_plano_usuario(db, usuario_id)

        # Se enviou lista de arquivos no carrossel
        lista_final_arquivos = []
        if dados.arquivos and len(dados.arquivos) > 0:
            lista_final_arquivos = [a for a in dados.arquivos if a and a.strip()]
        elif dados.arquivoUrl:
            lista_final_arquivos = [dados.arquivoUrl]

        # Validar plano Free vs Pro/Boost
        if len(lista_final_arquivos) > 1 and plano_tipo == "Free":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O plano Free permite postar apenas 1 página por obra. Faça upgrade para Artfolio Pro ou Boost para publicar carrosséis de imagens!"
            )

        url_principal = lista_final_arquivos[0] if lista_final_arquivos else dados.arquivoUrl
        arquivos_json = json.dumps(lista_final_arquivos) if len(lista_final_arquivos) > 1 else None

        nova_postagem = Postagem(
            idUsuario=usuario_id,
            legenda=dados.legenda,
            arquivoUrl=url_principal,
            arquivos_raw=arquivos_json,
            preco=dados.preco if dados.a_venda else None,
            a_venda=dados.a_venda,
            permite_download=dados.permite_download,
        )
        postagem_criada = PostagemRepository.criar(db, nova_postagem, categoria_ids=categoria_ids)

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

        categoria_ids = None
        if dados.idCategorias is not None:
            categoria_ids = list(dados.idCategorias)
        elif dados.idCategoria is not None:
            categoria_ids = [dados.idCategoria]
        elif dados.nomesCategorias is not None:
            categoria_ids = []
            for cat_nome in dados.nomesCategorias:
                if cat_nome and cat_nome.strip():
                    nome_limpo = cat_nome.strip()
                    cat = db.query(Categoria).filter(
                        func.lower(Categoria.nomeCategoria) == nome_limpo.lower(),
                        Categoria.deletado == False
                    ).first()
                    if not cat:
                        cat = Categoria(nomeCategoria=nome_limpo)
                        db.add(cat)
                        db.flush()
                    if cat and cat.id not in categoria_ids:
                        categoria_ids.append(cat.id)

        if dados.legenda is not None:
            obra.legenda = dados.legenda
        if dados.arquivoUrl is not None:
            obra.arquivoUrl = dados.arquivoUrl
        if dados.a_venda is not None:
            obra.a_venda = dados.a_venda
            if not dados.a_venda:
                obra.preco = None
        if dados.preco is not None and obra.a_venda:
            obra.preco = dados.preco
        if dados.permite_download is not None:
            obra.permite_download = dados.permite_download

        postagem_atualizada = PostagemRepository.atualizar(db, obra, categoria_ids=categoria_ids)

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

    @staticmethod
    def alternar_curtida(db: Session, usuario_id: int, postagem_id: int) -> dict:
        """
        Alterna a curtida em uma postagem: curte se não curtiu, ou descurte se já curtiu.
        Invalida o cache do feed no Redis e notifica via Redis Pub/Sub.
        """
        from app.services.curtida_service import CurtidaService
        curtida_existente = CurtidaRepository.buscar(db, usuario_id, postagem_id)
        if curtida_existente:
            CurtidaService.descurtir(db, usuario_id, postagem_id)
            curtido = False
        else:
            CurtidaService.curtir(db, usuario_id, postagem_id)
            curtido = True

        redis_client.delete_pattern("artfolio:obras:*")
        total_curtidas = CurtidaRepository.contar_por_postagem(db, postagem_id)
        return {
            "curtido": curtido,
            "total_curtidas": total_curtidas,
            "postagem_id": postagem_id
        }

    @staticmethod
    def adicionar_comentario(db: Session, usuario_id: int, postagem_id: int, conteudo: str) -> dict:
        """
        Adiciona comentário em uma obra, invalida o cache do feed e dispara notificação em tempo real.
        """
        from app.services.comentario_service import ComentarioService
        from app.schemas.comentario_schema import ComentarioCriar
        comentario = ComentarioService.criar_comentario(
            db, usuario_id, postagem_id, ComentarioCriar(conteudo=conteudo)
        )
        redis_client.delete_pattern("artfolio:obras:*")
        total_comentarios = ComentarioRepository.contar_por_postagem(db, postagem_id)
        return {
            "comentario": comentario,
            "total_comentarios": total_comentarios,
            "postagem_id": postagem_id
        }

    @staticmethod
    def alternar_fixar_obra(db: Session, postagem_id: int, usuario_id: int) -> Postagem:
        """
        Alterna a fixação de uma postagem no perfil do artista (Pin de até 3 postagens).
        Ao fixar, atribui o timestamp atual (fixado_em) para ordenação LIFO no topo.
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
                detail="Você só pode fixar postagens do seu próprio perfil."
            )

        # Se for fixar (atualmente não fixada)
        if not obra.fixado:
            total_fixadas = PostagemRepository.contar_fixadas(db, usuario_id)
            if total_fixadas >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Você já atingiu o limite de 3 postagens fixadas. Desafixe uma para fixar outra."
                )
            obra.fixado = True
            obra.fixado_em = datetime.now(timezone.utc)
        else:
            # Desafixar
            obra.fixado = False
            obra.fixado_em = None

        db.commit()
        db.refresh(obra)

        # Invalida o cache de obras
        redis_client.delete_pattern("artfolio:obras:*")

        return obra

