from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario_schema import UsuarioUpdateSchema, UsuarioSenhaSchema, UsuarioResposta
from app.schemas.seguidor_schema import SeguidorResposta
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
    - **fotoPerfil**: URL da imagem de perfil
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
