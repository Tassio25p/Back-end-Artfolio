from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario_schema import (
    UsuarioUpdateSchema,
    UsuarioSenhaSchema,
    UsuarioResposta,
    PerfilPublicoResposta
)
from app.schemas.seguidor_schema import SeguidorResposta, RelacionamentoStatusResposta, UsuarioRelacionamentoItem
from app.services.usuario_service import UsuarioService
from app.services.seguidor_service import SeguidorService
from app.controllers.auth_controller import obter_usuario_atual, obter_usuario_opcional
from app.models.usuario_model import Usuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get(
    "",
    response_model=List[PerfilPublicoResposta],
    status_code=status.HTTP_200_OK,
    summary="Listar artistas cadastrados"
)
@router.get(
    "/",
    response_model=List[PerfilPublicoResposta],
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
def listar_artistas(
    busca: Optional[str] = Query(None, description="Filtrar por nome ou bio"),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todos os artistas/usuários cadastrados no banco para o catálogo de busca.
    """
    return UsuarioService.listar_artistas(db, busca=busca)


@router.put(
    "/me",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Atualizar perfil do usuário autenticado"
)
def atualizar_perfil(
    dados: UsuarioUpdateSchema,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Atualiza os dados do perfil do usuário autenticado (incluindo trajetória, especializações e certificados).
    """
    return UsuarioService.atualizar_perfil(db, usuario_atual.id, dados)


@router.put(
    "/me/foto",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Atualizar foto de perfil do usuário autenticado"
)
def atualizar_foto_perfil(
    foto: UploadFile = File(..., description="Arquivo de imagem da foto de perfil (JPG, PNG ou WEBP, máx. 5MB)"),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Realiza o upload de uma nova foto de perfil em multipart/form-data.
    """
    return UsuarioService.atualizar_foto_perfil(db, usuario_atual.id, foto)


@router.post(
    "/me/certificados/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload de arquivo de certificado ou documento do portfólio"
)
def upload_certificado(
    arquivo: UploadFile = File(..., description="Arquivo PDF ou imagem do certificado (máx. 10MB)"),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um arquivo de certificado ou documento e retorna a URL pública relativa.
    """
    url_arquivo = UsuarioService.upload_documento_certificado(db, usuario_atual.id, arquivo)
    return {"url": url_arquivo, "nome": arquivo.filename}


@router.delete(
    "/me/foto",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Remover foto de perfil do usuário autenticado"
)
def remover_foto_perfil(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove a foto de perfil do usuário autenticado.
    """
    return UsuarioService.remover_foto_perfil(db, usuario_atual.id)


@router.patch(
    "/me/senha",
    status_code=status.HTTP_200_OK,
    summary="Alterar senha do usuário autenticado"
)
def alterar_senha(
    dados: UsuarioSenhaSchema,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Altera a senha do usuário autenticado.
    """
    return UsuarioService.alterar_senha(db, usuario_atual.id, dados)


# --- Endpoints de Seguir / Deixar de Seguir ---

@router.post(
    "/{id}/seguir",
    response_model=SeguidorResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Seguir um usuário / artista"
)
def seguir_usuario(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Registra que o usuário autenticado passou a seguir o usuário com ID {id}.
    """
    return SeguidorService.seguir(db, usuario_atual.id, id)


@router.delete(
    "/{id}/seguir",
    status_code=status.HTTP_200_OK,
    summary="Deixar de seguir um usuário / artista"
)
def deixar_de_seguir_usuario(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove o relacionamento de seguir entre o usuário autenticado e o usuário {id}.
    """
    return SeguidorService.deixar_de_seguir(db, usuario_atual.id, id)


@router.get(
    "/{id}",
    response_model=PerfilPublicoResposta,
    status_code=status.HTTP_200_OK,
    summary="Obter perfil público de um usuário"
)
def obter_perfil_usuario(
    id: int,
    usuario_atual: Optional[Usuario] = Depends(obter_usuario_opcional),
    db: Session = Depends(get_db)
):
    """
    Retorna o perfil público completo do usuário {id} com métricas reais,
    funcionando tanto para usuários autenticados quanto para visitantes.
    """
    me_id = usuario_atual.id if usuario_atual else None
    return UsuarioService.obter_perfil_publico(db, target_id=id, me_id=me_id)


@router.get(
    "/{id}/relacionamento",
    response_model=RelacionamentoStatusResposta,
    status_code=status.HTTP_200_OK,
    summary="Obter status do relacionamento com um usuário"
)
def obter_status_relacionamento(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna as flags de relacionamento entre o usuário logado e o usuário {id}.
    """
    return SeguidorService.obter_status_relacionamento(db, me_id=usuario_atual.id, target_id=id)


@router.get(
    "/{id}/seguidores",
    response_model=List[UsuarioRelacionamentoItem],
    status_code=status.HTTP_200_OK,
    summary="Listar seguidores de um usuário"
)
def listar_seguidores(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de usuários que seguem o perfil {id}.
    """
    return SeguidorService.listar_seguidores(db, target_id=id, me_id=usuario_atual.id)


@router.get(
    "/{id}/seguindo",
    response_model=List[UsuarioRelacionamentoItem],
    status_code=status.HTTP_200_OK,
    summary="Listar usuários que um perfil está seguindo"
)
def listar_seguindo(
    id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de usuários seguidos pelo perfil {id}.
    """
    return SeguidorService.listar_seguindo(db, target_id=id, me_id=usuario_atual.id)
