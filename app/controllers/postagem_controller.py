import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.config import settings
from app.schemas.postagem_schema import PostagemResposta, PostagemCriar, PostagemAtualizar
from app.schemas.comentario_schema import ComentarioResposta, ComentarioCriar
from app.schemas.curtida_schema import CurtidaResposta
from app.schemas.obra_salva_schema import SalvarStatusResposta
from app.schemas.denuncia_schema import DenunciaCriar, DenunciaResposta
from app.services.postagem_service import PostagemService
from app.services.media_service import MediaService
from app.services.curtida_service import CurtidaService
from app.services.comentario_service import ComentarioService
from app.services.obra_salva_service import ObraSalvaService
from app.services.denuncia_service import DenunciaService
from app.controllers.auth_controller import obter_usuario_atual, obter_usuario_opcional
from app.models.usuario_model import Usuario
from app.core.limiter import limiter

router = APIRouter(tags=["Obras / Postagens"])

@router.get("/postagens", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK)
@router.get("/postagens/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
@router.get("/obras", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, summary="Listar obras")
@router.get("/obras/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_obras(
    usuario_id: Optional[int] = Query(None, description="Filtrar obras por ID do usuário/artista"),
    categoria_id: Optional[int] = Query(None, description="Filtrar obras por ID da categoria"),
    busca: Optional[str] = Query(None, description="Buscar por palavra-chave"),
    usuario_atual: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db)
):
    """
    Retorna todas as obras ativas cadastradas na plataforma.
    Permite filtrar por usuário, categoria ou busca textual.
    """
    user_id = usuario_atual.id if usuario_atual else None
    return PostagemService.listar_obras(
        db,
        usuario_id=usuario_id,
        categoria_id=categoria_id,
        termo_busca=busca,
        usuario_atual_id=user_id
    )

@router.get("/categorias/desafio-atual", status_code=status.HTTP_200_OK, summary="Obter Desafio Semanal Ativo")
def obter_desafio_atual(db: Session = Depends(get_db)):
    """
    Retorna a categoria correspondente ao Desafio da Semana ativo atualmente (Art Prompt).
    """
    from app.models.categoria_model import Categoria
    desafio = db.query(Categoria).filter(
        Categoria.deletado == False,
        Categoria.is_desafio == True,
        Categoria.desafio_ativo == True
    ).first()
    
    if not desafio:
        # Se nenhum estiver ativo, tenta ativar o primeiro desafio disponível
        desafio = db.query(Categoria).filter(
            Categoria.deletado == False,
            Categoria.is_desafio == True
        ).order_by(Categoria.id.asc()).first()
        if desafio:
            from datetime import datetime, timezone
            desafio.desafio_ativo = True
            desafio.data_inicio_desafio = datetime.now(timezone.utc)
            db.commit()
            db.refresh(desafio)

    if not desafio:
        return None

    from datetime import datetime, timezone, timedelta
    prazo_dias = getattr(desafio, "prazo_dias", 7) or 7
    inicio = desafio.data_inicio_desafio
    fim = getattr(desafio, "data_fim_desafio", None)
    if inicio and not fim:
        fim = inicio + timedelta(days=prazo_dias)

    return {
        "id": desafio.id,
        "nomeCategoria": desafio.nomeCategoria,
        "is_desafio": True,
        "desafio_ativo": True,
        "prazo_dias": prazo_dias,
        "data_inicio_desafio": inicio.isoformat() if inicio else None,
        "data_fim_desafio": fim.isoformat() if fim else None,
    }

@router.get("/categorias", status_code=status.HTTP_200_OK, summary="Listar todas as categorias oficiais")
@router.get("/categorias/", status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_categorias(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de categorias oficiais cadastradas no PostgreSQL.
    Por padrão, oculta desafios semanais inativos/antigos da criação de novas obras.
    """
    from app.models.categoria_model import Categoria
    from sqlalchemy import or_

    query = db.query(Categoria).filter(Categoria.deletado == False)
    if not incluir_inativos:
        query = query.filter(
            or_(
                Categoria.is_desafio == False,
                Categoria.desafio_ativo == True
            )
        )
    categorias = query.order_by(Categoria.nomeCategoria.asc()).all()
    return [
        {
            "id": c.id,
            "nomeCategoria": c.nomeCategoria,
            "is_desafio": getattr(c, "is_desafio", False),
            "desafio_ativo": getattr(c, "desafio_ativo", False),
            "data_inicio_desafio": c.data_inicio_desafio.isoformat() if getattr(c, "data_inicio_desafio", None) else None
        }
        for c in categorias
    ]

@router.get("/postagens/salvas", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, summary="Listar minhas obras salvas")
@router.get("/postagens/salvas/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
@router.get("/obras/salvas", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_obras_salvas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna todas as obras salvas pelo usuário autenticado.
    """
    return ObraSalvaService.listar_salvas(db, usuario_atual.id)

@router.get("/postagens/{id}", response_model=PostagemResposta, status_code=status.HTTP_200_OK)
@router.get("/obras/{id}", response_model=PostagemResposta, status_code=status.HTTP_200_OK, summary="Obter obra por ID")
def obter_obra_por_id(
    id: int,
    request: Request,
    usuario_atual: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db)
):
    """
    Retorna os detalhes de uma obra específica através do seu ID com métricas sincronizadas.
    """
    user_id = usuario_atual.id if usuario_atual else None
    client_ip = request.client.host if request.client else None
    return PostagemService.buscar_obra_por_id(db, id, usuario_atual_id=user_id, client_ip=client_ip)

@router.get("/postagens/{id}/download", summary="Download do arquivo da obra")
@router.get("/obras/{id}/download", summary="Download do arquivo da obra", include_in_schema=False)
async def download_obra(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Realiza o download direto do arquivo original da obra caso o autor tenha habilitado 'permite_download'.
    Retorna FileResponse (ou stream com application/octet-stream) configurando o filename para download.
    """
    obra = PostagemService.buscar_obra_por_id(db, id)
    if not obra:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obra não encontrada."
        )

    if not obra.permite_download:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download não autorizado pelo autor."
        )

    url_arquivo = obra.arquivoUrl
    extensao = os.path.splitext(url_arquivo.split("?")[0])[1] or ".png"
    legenda_limpa = "".join(c for c in (obra.legenda or "obra") if c.isalnum() or c in ("-", "_")).strip()[:25]
    nome_arquivo = f"artfolio_obra_{obra.id}_{legenda_limpa or 'arquivo'}{extensao}"

    # 1. Se for arquivo armazenado localmente em /uploads/
    if url_arquivo.startswith("/uploads/"):
        relativo = url_arquivo[len("/uploads/"):]
        caminho_local = os.path.join(settings.UPLOAD_DIR, relativo)
        if os.path.exists(caminho_local):
            return FileResponse(
                path=caminho_local,
                filename=nome_arquivo,
                media_type="application/octet-stream"
            )

    # 2. Se for arquivo em disco com caminho absoluto existente
    if os.path.exists(url_arquivo):
        return FileResponse(
            path=url_arquivo,
            filename=nome_arquivo,
            media_type="application/octet-stream"
        )

    # 3. Se for arquivo remoto (Cloudinary ou outra CDN)
    if url_arquivo.startswith(("http://", "https://")):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url_arquivo)
                resp.raise_for_status()
                return Response(
                    content=resp.content,
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'}
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha ao transferir arquivo para download: {str(e)}"
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Arquivo físico não localizado para download."
    )

@router.post("/postagens", response_model=PostagemResposta, status_code=status.HTTP_201_CREATED, summary="Criar postagem")
@router.post("/obras", response_model=PostagemResposta, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def criar_postagem(
    dados: PostagemCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Cria e publica diretamente uma nova obra (postagem) na plataforma.
    """
    return PostagemService.criar_postagem(db, usuario_atual.id, dados)

@router.put("/postagens/{id}", response_model=PostagemResposta, status_code=status.HTTP_200_OK, summary="Atualizar postagem")
def atualizar_postagem(
    id: int,
    dados: PostagemAtualizar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Atualiza os dados de uma obra existente.
    """
    return PostagemService.atualizar_postagem(db, id, usuario_atual.id, dados)

@router.post("/postagens/upload", status_code=status.HTTP_201_CREATED, summary="Fazer upload de imagem de obra")
@limiter.limit("20/minute")
def upload_imagem_obra(
    request: Request,
    arquivo: UploadFile = File(...),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Recebe um arquivo de imagem (PNG, JPG, WEBP), valida limites de MB do plano sem compressão
    e faz upload seguro preservando a qualidade 100% original.
    """
    from app.services.plano_service import PlanoService
    plano_tipo = PlanoService.obter_tipo_plano_usuario(db, usuario_atual.id)
    
    limites_por_plano = {
        "Free": 10,
        "Pro": 50,
        "Boost": 100
    }
    max_mb = limites_por_plano.get(plano_tipo, 10)

    secure_url = MediaService.upload_imagem(arquivo, folder="artfolio/postagens", max_size_mb=max_mb)
    return {"url": secure_url, "nome": arquivo.filename, "limite_mb": max_mb}

@router.delete("/postagens/{id}", status_code=status.HTTP_200_OK, summary="Excluir postagem")
def deletar_postagem(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove (soft delete) uma obra existente.
    """
    PostagemService.deletar_postagem(db, id, usuario_atual.id, usuario_atual.tipo_conta)
    return {"message": "Postagem removida com sucesso."}

@router.patch("/postagens/{id}/fixar", response_model=PostagemResposta, status_code=status.HTTP_200_OK, summary="Fixar ou desafixar obra no perfil")
@router.patch("/obras/{id}/fixar", response_model=PostagemResposta, status_code=status.HTTP_200_OK, include_in_schema=False)
@router.post("/postagens/{id}/fixar", response_model=PostagemResposta, status_code=status.HTTP_200_OK, include_in_schema=False)
@router.post("/obras/{id}/fixar", response_model=PostagemResposta, status_code=status.HTTP_200_OK, include_in_schema=False)
def alternar_fixar_postagem(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Alterna o status de fixação (Pin de até 3 postagens) de uma obra no perfil do artista.
    """
    return PostagemService.alternar_fixar_obra(db, id, usuario_atual.id)


# --- Endpoints de Curtidas (Likes) ---

@router.post("/postagens/{id}/like", response_model=CurtidaResposta, status_code=status.HTTP_201_CREATED, summary="Curtir postagem")
@router.post("/postagens/{id}/curtir", response_model=CurtidaResposta, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@limiter.limit("30/minute")
def curtir_postagem(
    request: Request,
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra uma curtida (like) do usuário autenticado na postagem indicada.
    """
    return CurtidaService.curtir(db, usuario_atual.id, id)

@router.delete("/postagens/{id}/like", status_code=status.HTTP_200_OK, summary="Remover curtida da postagem")
@router.delete("/postagens/{id}/curtir", status_code=status.HTTP_200_OK, include_in_schema=False)
def descurtir_postagem(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove a curtida do usuário autenticado na postagem indicada.
    """
    return CurtidaService.descurtir(db, usuario_atual.id, id)


# --- Endpoints de Comentários ---

@router.post("/postagens/{id}/comentarios", response_model=ComentarioResposta, status_code=status.HTTP_201_CREATED, summary="Comentar em uma postagem")
@limiter.limit("30/minute")
def criar_comentario(
    request: Request,
    id: int,
    dados: ComentarioCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Adiciona um novo comentário à postagem indicada.
    """
    return ComentarioService.criar_comentario(db, usuario_atual.id, id, dados)

@router.get("/postagens/{id}/comentarios", response_model=List[ComentarioResposta], status_code=status.HTTP_200_OK, summary="Listar comentários de uma postagem")
def listar_comentarios(id: int, db: Session = Depends(get_db)):
    """
    Retorna todos os comentários ativos da postagem ordenada por data de criação.
    """
    return ComentarioService.listar_comentarios(db, id)

@router.delete("/comentarios/{id}", status_code=status.HTTP_200_OK, summary="Excluir comentário")
def deletar_comentario(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove (soft delete) um comentário existente.
    """
    return ComentarioService.deletar_comentario(db, usuario_atual.id, id, usuario_atual.tipo_conta)


# --- Endpoints de Obra Salva (Saved Works / Favoritos) ---
 
@router.post("/postagens/{id}/salvar", response_model=SalvarStatusResposta, status_code=status.HTTP_201_CREATED, summary="Salvar uma obra")
def salvar_obra(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra o salvamento da obra indicada para o usuário autenticado.
    """
    ObraSalvaService.salvar_obra(db, usuario_atual.id, id)
    return {"message": "Obra salva com sucesso.", "salvo": True}

@router.delete("/postagens/{id}/salvar", status_code=status.HTTP_200_OK, summary="Remover obra dos salvos")
def remover_salvo(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove o salvamento da obra para o usuário autenticado.
    """
    return ObraSalvaService.remover_salvo(db, usuario_atual.id, id)

@router.get("/postagens/{id}/salvo", status_code=status.HTTP_200_OK, summary="Checar se obra está salva")
def checar_salvo(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna se a obra indicada está salva pelo usuário autenticado.
    """
    return ObraSalvaService.checar_salvo(db, usuario_atual.id, id)


# --- Endpoints de Denúncias ---

@router.post("/postagens/{id}/denunciar", response_model=DenunciaResposta, status_code=status.HTTP_201_CREATED, summary="Denunciar uma obra")
def denunciar_obra(
    id: int,
    dados: DenunciaCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra uma denúncia contra a obra indicada.
    """
    return DenunciaService.criar_denuncia(db, usuario_atual.id, id, dados)
