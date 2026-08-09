from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.postagem_schema import PostagemResposta, PostagemCriar, PostagemAtualizar
from app.schemas.comentario_schema import ComentarioResposta, ComentarioCriar
from app.schemas.curtida_schema import CurtidaResposta
from app.services.postagem_service import PostagemService
from app.services.curtida_service import CurtidaService
from app.services.comentario_service import ComentarioService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario

router = APIRouter(tags=["Obras / Postagens"])

@router.get("/postagens", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK)
@router.get("/postagens/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
@router.get("/obras", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, summary="Listar obras")
@router.get("/obras/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_obras(
    usuario_id: Optional[int] = Query(None, description="Filtrar obras por ID do usuário/artista"),
    categoria_id: Optional[int] = Query(None, description="Filtrar obras por ID da categoria"),
    db: Session = Depends(get_db)
):
    """
    Retorna todas as obras (postagens) ativas cadastradas na plataforma.
    Permite filtrar opcionalmente por usuário (artista) e por categoria.
    """
    return PostagemService.listar_obras(db, usuario_id=usuario_id, categoria_id=categoria_id)

@router.get("/postagens/{id}", response_model=PostagemResposta, status_code=status.HTTP_200_OK, include_in_schema=False)
@router.get("/obras/{id}", response_model=PostagemResposta, status_code=status.HTTP_200_OK, summary="Obter obra por ID")
def obter_obra_por_id(id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de uma obra específica através do seu ID.
    """
    return PostagemService.buscar_obra_por_id(db, id)

@router.post("/postagens", response_model=PostagemResposta, status_code=status.HTTP_201_CREATED, summary="Criar postagem")
def criar_postagem(
    dados: PostagemCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Cria uma nova obra (postagem) na plataforma.

    Requer autenticação JWT. O autor da postagem é definido automaticamente
    como o usuário logado.
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

    Somente o proprietário da obra pode atualizá-la (HTTP 403 caso contrário).
    """
    return PostagemService.atualizar_postagem(db, id, usuario_atual.id, dados)

@router.delete("/postagens/{id}", status_code=status.HTTP_200_OK, summary="Excluir postagem")
def deletar_postagem(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove (soft delete) uma obra existente.

    Apenas o proprietário da obra ou admins/moderadores podem excluí-la.
    """
    PostagemService.deletar_postagem(db, id, usuario_atual.id, usuario_atual.tipo_conta)
    return {"message": "Postagem removida com sucesso."}


# --- Endpoints de Curtidas (Likes) ---

@router.post("/postagens/{id}/like", response_model=CurtidaResposta, status_code=status.HTTP_201_CREATED, summary="Curtir postagem")
def curtir_postagem(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra uma curtida (like) do usuário autenticado na postagem indicada.
    Retorna erro caso a postagem não exista ou se o usuário já tiver curtido.
    """
    return CurtidaService.curtir(db, usuario_atual.id, id)

@router.delete("/postagens/{id}/like", status_code=status.HTTP_200_OK, summary="Remover curtida da postagem")
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
def criar_comentario(
    id: int,
    dados: ComentarioCriar,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Adiciona um novo comentário à postagem indicada.
    Requer autenticação JWT e texto de 1 a 500 caracteres.
    """
    return ComentarioService.criar_comentario(db, usuario_atual.id, id, dados)

@router.get("/postagens/{id}/comentarios", response_model=List[ComentarioResposta], status_code=status.HTTP_200_OK, summary="Listar comentários de uma postagem")
def listar_comentarios(id: int, db: Session = Depends(get_db)):
    """
    Retorna todos os comentários ativos da postagem ordenada por data de criação.
    """
    return ComentarioService.listar_comentarios(db, id)

from app.schemas.obra_salva_schema import ObraSalvaResposta, SalvarStatusResposta
from app.schemas.denuncia_schema import DenunciaCriar, DenunciaResposta
from app.services.obra_salva_service import ObraSalvaService
from app.services.denuncia_service import DenunciaService


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


# --- Endpoints de Obra Salva (Saved Works) ---

@router.get("/postagens/salvas", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, summary="Listar minhas obras salvas")
@router.get("/postagens/salvas/", response_model=List[PostagemResposta], status_code=status.HTTP_200_OK, include_in_schema=False)
def listar_obras_salvas(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna todas as obras salvas pelo usuário autenticado.
    """
    return ObraSalvaService.listar_salvas(db, usuario_atual.id)


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
    Requer motivo obrigatório e impede auto-denúncia ou denúncias duplicadas.
    """
    return DenunciaService.criar_denuncia(db, usuario_atual.id, id, dados)

