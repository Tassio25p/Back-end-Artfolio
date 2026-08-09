from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario_schema import UsuarioUpdateSchema, UsuarioSenhaSchema, UsuarioResposta, PerfilPublicoResposta
from app.schemas.seguidor_schema import SeguidorResposta, RelacionamentoStatusResposta, UsuarioRelacionamentoItem
from app.services.usuario_service import UsuarioService
from app.services.seguidor_service import SeguidorService
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.put(
    "/me",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Atualizar perfil do usuário autenticado",
    responses={
        200: {"description": "Perfil atualizado com sucesso."},
        400: {"description": "Dados inválidos na requisição."},
        401: {"description": "Token JWT ausente ou inválido."},
        404: {"description": "Usuário não encontrado."},
        422: {"description": "Erro de validação nos campos enviados."},
        500: {"description": "Erro interno do servidor."},
    }
)
def atualizar_perfil(
    dados: UsuarioUpdateSchema,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Atualiza os dados do perfil do usuário autenticado.

    Permite a edição parcial dos seguintes campos:
    - **nome**: Nome completo (mín. 3, máx. 100 caracteres)
    - **telefone**: Telefone com DDD (10-11 dígitos)
    - **biografia**: Texto livre (máx. 1000 caracteres)
    - **portfolio**: URL do portfólio
    - **instagram**: Handle ou URL do Instagram
    - **behance**: Handle ou URL do Behance
    - **website**: URL do site pessoal (http/https)

    Somente os campos enviados no body serão atualizados.
    Campos ausentes permanecem inalterados.

    **Autenticação**: Requer Bearer Token JWT válido.
    O usuário só pode editar seu próprio perfil.
    """
    return UsuarioService.atualizar_perfil(db, usuario_atual.id, dados)


@router.put(
    "/me/foto",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Atualizar foto de perfil do usuário autenticado",
    responses={
        200: {"description": "Foto de perfil atualizada com sucesso."},
        400: {"description": "Arquivo inválido, vazio, formato não suportado ou excede 5MB."},
        401: {"description": "Token JWT ausente ou inválido."},
        404: {"description": "Usuário não encontrado."},
        500: {"description": "Erro ao salvar a foto de perfil."},
    }
)
def atualizar_foto_perfil(
    foto: UploadFile = File(..., description="Arquivo de imagem da foto de perfil (JPG, PNG ou WEBP, máx. 5MB)"),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Realiza o upload de uma nova foto de perfil em multipart/form-data.

    O arquivo é validado (MIME type, extensão, tamanho máximo de 5MB) e armazenado
    no diretório de uploads do servidor. O usuário autenticado é identificado pelo token JWT.
    """
    return UsuarioService.atualizar_foto_perfil(db, usuario_atual.id, foto)


@router.delete(
    "/me/foto",
    response_model=UsuarioResposta,
    status_code=status.HTTP_200_OK,
    summary="Remover foto de perfil do usuário autenticado",
    responses={
        200: {"description": "Foto de perfil removida com sucesso."},
        401: {"description": "Token JWT ausente ou inválido."},
        404: {"description": "Usuário não encontrado."},
    }
)
def remover_foto_perfil(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Remove a foto de perfil do usuário autenticado, voltando ao avatar padrão.
    """
    return UsuarioService.remover_foto_perfil(db, usuario_atual.id)



@router.patch(
    "/me/senha",
    status_code=status.HTTP_200_OK,
    summary="Alterar senha do usuário autenticado",
    responses={
        200: {"description": "Senha alterada com sucesso.", "content": {"application/json": {"example": {"message": "Senha alterada com sucesso."}}}},
        400: {"description": "Senha atual incorreta ou dados inválidos."},
        401: {"description": "Token JWT ausente ou inválido."},
        404: {"description": "Usuário não encontrado."},
        422: {"description": "Erro de validação nos campos enviados."},
        500: {"description": "Erro interno do servidor."},
    }
)
def alterar_senha(
    dados: UsuarioSenhaSchema,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Altera a senha do usuário autenticado.

    Recebe a senha atual para confirmação de identidade,
    a nova senha e a confirmação da nova senha.

    **Regras de validação:**
    - A senha atual deve estar correta
    - A nova senha deve ter no mínimo 6 caracteres
    - A confirmação deve ser idêntica à nova senha

    **Autenticação**: Requer Bearer Token JWT válido.
    A senha é criptografada com bcrypt antes de ser salva.
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
    Não é permitido seguir a si mesmo ou seguir o mesmo usuário duas vezes.
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
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Retorna o perfil público completo do usuário {id},
    incluindo contagens de seguidores, seguindo, obras e o status do relacionamento com o usuário autenticado.
    """
    return UsuarioService.obter_perfil_publico(db, target_id=id, me_id=usuario_atual.id)


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
    Retorna as flags de relacionamento entre o usuário logado e o usuário {id} (seguindo, segueDeVolta, isMe, etc).
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
    Retorna a lista de usuários que seguem o perfil {id},
    com flags informando se o usuário logado também os segue (para o botão 'Seguir de volta').
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
