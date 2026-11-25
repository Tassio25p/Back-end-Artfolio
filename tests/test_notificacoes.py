"""
Suíte de Testes Automatizados da Central de Notificações.
Valida conformidade com os requisitos da Fase 3:
- GET /notificacoes (filtros por tipo, apenas_nao_lidas, limite, offset, contadores)
- PATCH /notificacoes/{id}/ler (permissão, persistência, status lida)
- PATCH /notificacoes/ler-todas (atualização em lote, status sucesso)
- DELETE /notificacoes/{id} (soft delete, isolamento entre usuários)
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db, SessionLocal
from app.models.usuario_model import Usuario
from app.models.notificacao_model import Notificacao
from app.services.usuario_service import UsuarioService


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.core.security import criar_token_acesso


@pytest.fixture(scope="module")
def setup_usuarios(db_session: Session):
    """
    Recupera ou cria 2 usuários para teste de permissão e isolamento.
    """
    usuarios = db_session.query(Usuario).order_by(Usuario.id.asc()).all()
    if len(usuarios) >= 2:
        user_a = usuarios[0]
        user_b = usuarios[1]
    else:
        user_a = Usuario(nome="Notif User A", email=f"notif_a_{int(datetime.now().timestamp())}@artfolio.com")
        user_b = Usuario(nome="Notif User B", email=f"notif_b_{int(datetime.now().timestamp())}@artfolio.com")
        db_session.add_all([user_a, user_b])
        db_session.commit()
        db_session.refresh(user_a)
        db_session.refresh(user_b)

    token_a = criar_token_acesso({"sub": str(user_a.id)})
    token_b = criar_token_acesso({"sub": str(user_b.id)})

    return {
        "user_a": user_a,
        "user_b": user_b,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
    }



@pytest.fixture
def notificacoes_massa(db_session: Session, setup_usuarios):
    """
    Cria uma massa controlada de notificações para o user_a:
    - 2 do tipo 'mensagem' (1 lida, 1 não lida)
    - 2 do tipo 'curtida' (não lidas)
    - 1 do tipo 'proposta' (não lida)
    """
    user_a = setup_usuarios["user_a"]

    # Limpar notificações anteriores de teste
    db_session.query(Notificacao).filter(Notificacao.idUsuario == user_a.id).delete()
    db_session.commit()

    n1 = Notificacao(
        idUsuario=user_a.id,
        tipo="mensagem",
        titulo="Nova Mensagem",
        mensagem="Olá, tudo bem com a sua obra?",
        lida=False,
        dataCriacao=datetime.utcnow() - timedelta(minutes=5),
        referencia_id=10,
        link_acao="/mensagens?chat=10"
    )
    n2 = Notificacao(
        idUsuario=user_a.id,
        tipo="mensagem",
        titulo="Mensagem Lida",
        mensagem="Mensagem de conversa anterior já visualizada.",
        lida=True,
        dataCriacao=datetime.utcnow() - timedelta(minutes=10),
        referencia_id=10,
        link_acao="/mensagens?chat=10"
    )
    n3 = Notificacao(
        idUsuario=user_a.id,
        tipo="curtida",
        titulo="Nova Curtida",
        mensagem="Um usuário curtiu sua arte.",
        lida=False,
        dataCriacao=datetime.utcnow() - timedelta(minutes=2),
        referencia_id=101,
        link_acao="/feed"
    )
    n4 = Notificacao(
        idUsuario=user_a.id,
        tipo="curtida",
        titulo="Outra Curtida",
        mensagem="Sua arte recebeu mais um coração.",
        lida=False,
        dataCriacao=datetime.utcnow() - timedelta(minutes=1),
        referencia_id=102,
        link_acao="/feed"
    )
    n5 = Notificacao(
        idUsuario=user_a.id,
        tipo="proposta",
        titulo="Nova Proposta",
        mensagem="Você recebeu uma proposta comercial de encomenda.",
        lida=False,
        dataCriacao=datetime.utcnow(),
        referencia_id=50,
        link_acao="/propostas/50"
    )

    db_session.add_all([n1, n2, n3, n4, n5])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)
    db_session.refresh(n3)
    db_session.refresh(n4)
    db_session.refresh(n5)

    return [n1, n2, n3, n4, n5]


# =====================================================================
# 1. TESTES DE LISTAGEM COM FILTROS E PAGINAÇÃO (GET /notificacoes)
# =====================================================================

def test_1_1_listar_notificacoes_estrutura_resposta(client, setup_usuarios, notificacoes_massa):
    """
    Valida formato padrão exigido:
    {
      "total_nao_lidas": total_nao_lidas_do_usuario,
      "total": total_registros_filtrados,
      "notificacoes": [ ... ]
    }
    """
    headers = setup_usuarios["headers_a"]
    res = client.get("/notificacoes", headers=headers)
    assert res.status_code == 200
    dados = res.json()

    assert "total_nao_lidas" in dados
    assert "total" in dados
    assert "notificacoes" in dados
    assert isinstance(dados["notificacoes"], list)

    # user_a tem 4 não lidas e 5 no total
    assert dados["total_nao_lidas"] == 4
    assert dados["total"] == 5
    assert len(dados["notificacoes"]) == 5

    # Valida estrutura individual dos itens
    item = dados["notificacoes"][0]
    assert "id" in item
    assert "usuario_id" in item
    assert "tipo" in item
    assert "titulo" in item
    assert "conteudo" in item
    assert "referencia_id" in item
    assert "link_acao" in item
    assert "lida" in item
    assert "criado_em" in item


def test_1_2_listar_notificacoes_filtro_tipo(client, setup_usuarios, notificacoes_massa):
    """
    Valida filtragem por categoria/tipo ('mensagem', 'curtida', 'proposta').
    """
    headers = setup_usuarios["headers_a"]

    # 1. Filtro 'mensagem' -> deve trazer 2 mensagens
    res_msg = client.get("/notificacoes?tipo=mensagem", headers=headers)
    assert res_msg.status_code == 200
    dados_msg = res_msg.json()
    assert dados_msg["total"] == 2
    for n in dados_msg["notificacoes"]:
        assert n["tipo"].lower() in ("mensagem", "message")

    # 2. Filtro 'curtida' -> deve trazer 2 curtidas
    res_curtida = client.get("/notificacoes?tipo=curtida", headers=headers)
    assert res_curtida.status_code == 200
    dados_curtida = res_curtida.json()
    assert dados_curtida["total"] == 2

    # 3. Filtro 'proposta' -> deve trazer 1 proposta
    res_prop = client.get("/notificacoes?tipo=proposta", headers=headers)
    assert res_prop.status_code == 200
    dados_prop = res_prop.json()
    assert dados_prop["total"] == 1


def test_1_3_listar_notificacoes_filtro_apenas_nao_lidas(client, setup_usuarios, notificacoes_massa):
    """
    Valida parâmetro apenas_nao_lidas=true.
    """
    headers = setup_usuarios["headers_a"]
    res = client.get("/notificacoes?apenas_nao_lidas=true", headers=headers)
    assert res.status_code == 200
    dados = res.json()

    assert dados["total"] == 4
    for n in dados["notificacoes"]:
        assert n["lida"] is False


def test_1_4_listar_notificacoes_paginacao(client, setup_usuarios, notificacoes_massa):
    """
    Valida limites e offsets na paginação.
    """
    headers = setup_usuarios["headers_a"]

    # Página 1 com limite 2
    res_p1 = client.get("/notificacoes?limite=2&offset=0", headers=headers)
    assert res_p1.status_code == 200
    dados_p1 = res_p1.json()
    assert len(dados_p1["notificacoes"]) == 2
    assert dados_p1["total"] == 5

    # Página 2 com limite 2 e offset 2
    res_p2 = client.get("/notificacoes?limite=2&offset=2", headers=headers)
    assert res_p2.status_code == 200
    dados_p2 = res_p2.json()
    assert len(dados_p2["notificacoes"]) == 2

    # Os IDs não podem se sobrepor
    ids_p1 = {n["id"] for n in dados_p1["notificacoes"]}
    ids_p2 = {n["id"] for n in dados_p2["notificacoes"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_1_5_listar_notificacoes_sem_token_retorna_401_ou_403(client):
    """
    Acesso não autenticado deve ser rejeitado.
    """
    res = client.get("/notificacoes")
    assert res.status_code in (401, 403)


# =====================================================================
# 2. TESTES DE MARCAÇÃO INDIVIDUAL COMO LIDA (PATCH /notificacoes/{id}/ler)
# =====================================================================

def test_2_1_marcar_como_lida_sucesso(client, db_session, setup_usuarios, notificacoes_massa):
    """
    Sucesso ao marcar notificação própria como lida.
    """
    headers_a = setup_usuarios["headers_a"]
    notif = notificacoes_massa[0]  # estava lida=False
    assert notif.lida is False

    res = client.patch(f"/notificacoes/{notif.id}/ler", headers=headers_a)
    assert res.status_code == 200
    dados = res.json()
    assert dados["id"] == notif.id
    assert dados["lida"] is True

    # Validação direta no banco de dados
    db_session.expire_all()
    notif_db = db_session.query(Notificacao).filter(Notificacao.id == notif.id).first()
    assert notif_db.lida is True


def test_2_2_marcar_como_lida_outro_usuario_retorna_403(client, setup_usuarios, notificacoes_massa):
    """
    Impedir que usuário tente marcar notificação alheia como lida (403 Forbidden).
    """
    headers_b = setup_usuarios["headers_b"]  # Invasor
    notif = notificacoes_massa[2]

    res = client.patch(f"/notificacoes/{notif.id}/ler", headers=headers_b)
    assert res.status_code == 403
    assert "permissão" in res.json().get("detail", "").lower()


def test_2_3_marcar_como_lida_inexistente_retorna_404(client, setup_usuarios):
    """
    Retorna 404 para ID inexistente.
    """
    headers_a = setup_usuarios["headers_a"]
    res = client.patch("/notificacoes/999999/ler", headers=headers_a)
    assert res.status_code == 404


# =====================================================================
# 3. TESTES DE MARCAÇÃO EM LOTE COMO LIDAS (PATCH /notificacoes/ler-todas)
# =====================================================================

def test_3_1_marcar_todas_como_lidas_sucesso(client, db_session, setup_usuarios, notificacoes_massa):
    """
    Atualiza em lote todas as notificações não lidas do usuário.
    """
    headers_a = setup_usuarios["headers_a"]
    user_a = setup_usuarios["user_a"]

    res = client.patch("/notificacoes/ler-todas", headers=headers_a)
    assert res.status_code == 200
    dados = res.json()
    assert dados.get("status") == "sucesso"
    assert "total_atualizadas" in dados
    assert dados["total_atualizadas"] >= 1

    # Validação no banco: nenhuma notificação de user_a deve estar lida=False
    db_session.expire_all()
    restantes = db_session.query(Notificacao).filter(
        Notificacao.idUsuario == user_a.id,
        Notificacao.lida == False,
        Notificacao.deletado == False
    ).count()
    assert restantes == 0


# =====================================================================
# 4. TESTES DE EXCLUSÃO / SOFT DELETE (DELETE /notificacoes/{id})
# =====================================================================

def test_4_1_deletar_notificacao_sucesso_soft_delete(client, db_session, setup_usuarios, notificacoes_massa):
    """
    Soft delete de notificação própria:
    - Retorna 200 OK com status "sucesso".
    - Registro continua existindo no banco com deletado=True.
    """
    headers_a = setup_usuarios["headers_a"]
    notif = notificacoes_massa[4]

    res = client.delete(f"/notificacoes/{notif.id}", headers=headers_a)
    assert res.status_code == 200
    assert res.json().get("status") == "sucesso"

    # Confirmação no PostgreSQL
    db_session.expire_all()
    notif_db = db_session.query(Notificacao).filter(Notificacao.id == notif.id).first()
    assert notif_db is not None, "Registro foi excluído fisicamente (esperado soft delete)!"
    assert notif_db.deletado is True
    assert notif_db.dataDelecao is not None


def test_4_2_deletar_notificacao_outro_usuario_retorna_403(client, db_session, setup_usuarios, notificacoes_massa):
    """
    Impedir que usuário delete notificação que não lhe pertence (403 Forbidden).
    """
    headers_b = setup_usuarios["headers_b"]
    notif = notificacoes_massa[1]

    res = client.delete(f"/notificacoes/{notif.id}", headers=headers_b)
    assert res.status_code == 403
    assert "permissão" in res.json().get("detail", "").lower()

    # Confirmação de integridade no banco
    db_session.expire_all()
    notif_db = db_session.query(Notificacao).filter(Notificacao.id == notif.id).first()
    assert notif_db.deletado is False


def test_4_3_deletar_notificacao_inexistente_retorna_404(client, setup_usuarios):
    """
    Retorna 404 para exclusão de notificação inexistente.
    """
    headers_a = setup_usuarios["headers_a"]
    res = client.delete("/notificacoes/999999", headers=headers_a)
    assert res.status_code == 404
