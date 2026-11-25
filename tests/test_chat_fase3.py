"""
Suíte de Testes Automatizados - Fase 3 do Chat (Artfolio)
=========================================================
Cobre as regras de negócio, segurança e moderação do chat:
1. Edição de Mensagens (PATCH /chat/mensagens/{id}):
   - 1.1: Sucesso ao editar mensagem própria dentro de 15 minutos (retorno 200, texto atualizado e campo editado_em preenchido).
   - 1.2: Erro 403 se outro usuário tentar editar mensagem que não foi ele quem enviou (e 401 sem auth).
   - 1.3: Erro 400 se a mensagem foi enviada há mais de 15 minutos (simulando 16 minutos no passado).

2. Exclusão Segura / Soft Delete (DELETE /chat/mensagens/{id}):
   - 2.1: Sucesso ao solicitar exclusão (retorno 200).
   - 2.2: Verificação no banco: confirmar que a mensagem AINDA EXISTE na tabela, com deletado_em e deletado_por_id preenchidos.
   - 2.3: Impedir que usuário que não participa da conversa delete a mensagem (retorno 403).

3. Sistema de Denúncias (POST /chat/denuncias):
   - 3.1: Envio bem-sucedido de denúncia com payload completo (retorno 201 Created).
   - 3.2: Verificação no banco: confirmar que a denúncia foi persistida com status 'pendente' e dados corretos.
   - 3.3: Erro 422 se campos obrigatórios não forem informados.
   - 3.4: Erro 400 ao tentar denunciar a si mesmo (auto-denúncia).
   - 3.5: Erro 403 se usuário não participa da conversa que está denunciando.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.usuario_model import Usuario
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.denuncia_chat_model import DenunciaChat
from app.core.security import criar_token_acesso


@pytest.fixture(scope="module")
def client():
    """Fixture que provê o cliente de testes da aplicação FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def db_session():
    """Fixture que provê uma sessão direta com o banco PostgreSQL para setup e asserções."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_chat(db_session):
    """
    Garante a existência de 3 usuários e 1 conversa de teste:
    - user_a: Remetente e participante da conversa
    - user_b: Destinatário e participante da conversa
    - user_c: Usuário externo que NÃO participa da conversa
    Gera tokens JWT e headers de autenticação para cada um.
    """
    # 1. Obter ou criar os 3 usuários
    usuarios = db_session.query(Usuario).order_by(Usuario.id.asc()).all()
    
    if len(usuarios) < 3:
        # Cria usuários de teste se não existirem no banco
        user_a = Usuario(nome="Remetente Teste", email=f"remetente_{int(datetime.now().timestamp())}@artfolio.com")
        user_b = Usuario(nome="Destinatario Teste", email=f"destinatario_{int(datetime.now().timestamp())}@artfolio.com")
        user_c = Usuario(nome="Externo Teste", email=f"externo_{int(datetime.now().timestamp())}@artfolio.com")
        db_session.add_all([user_a, user_b, user_c])
        db_session.commit()
        db_session.refresh(user_a)
        db_session.refresh(user_b)
        db_session.refresh(user_c)
    else:
        user_a = usuarios[0]
        user_b = usuarios[2] if len(usuarios) > 2 else usuarios[1]
        user_c = usuarios[1] if len(usuarios) > 2 else None

    # 2. Obter ou criar a conversa entre user_a e user_b
    conversa = (
        db_session.query(Conversa)
        .join(ConversaUsuario, Conversa.id == ConversaUsuario.idConversa)
        .filter(ConversaUsuario.idUsuario == user_a.id)
        .first()
    )

    if not conversa:
        conversa = Conversa()
        db_session.add(conversa)
        db_session.commit()
        db_session.refresh(conversa)

        part_a = ConversaUsuario(idConversa=conversa.id, idUsuario=user_a.id)
        part_b = ConversaUsuario(idConversa=conversa.id, idUsuario=user_b.id)
        db_session.add_all([part_a, part_b])
        db_session.commit()
    else:
        # Garante que user_a e user_b são participantes
        part_a = db_session.query(ConversaUsuario).filter_by(idConversa=conversa.id, idUsuario=user_a.id).first()
        if not part_a:
            db_session.add(ConversaUsuario(idConversa=conversa.id, idUsuario=user_a.id))
        part_b = db_session.query(ConversaUsuario).filter_by(idConversa=conversa.id, idUsuario=user_b.id).first()
        if not part_b:
            db_session.add(ConversaUsuario(idConversa=conversa.id, idUsuario=user_b.id))
        db_session.commit()

    # 3. Garantir que user_c NÃO participa desta conversa
    if user_c:
        db_session.query(ConversaUsuario).filter_by(idConversa=conversa.id, idUsuario=user_c.id).delete()
        db_session.commit()

    # 4. Gerar tokens de autenticação
    token_a = criar_token_acesso({"sub": str(user_a.id)})
    token_b = criar_token_acesso({"sub": str(user_b.id)})
    token_c = criar_token_acesso({"sub": str(user_c.id)}) if user_c else ""

    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "conversa": conversa,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
        "headers_c": {"Authorization": f"Bearer {token_c}"},
    }


@pytest.fixture
def mensagem_teste(db_session, setup_chat):
    """
    Cria uma mensagem de teste enviada pelo user_a dentro da conversa de teste.
    Remove a mensagem ao término do teste para isolamento.
    """
    user_a = setup_chat["user_a"]
    conversa = setup_chat["conversa"]

    msg = Mensagem(
        idRemetente=user_a.id,
        idConversa=conversa.id,
        conteudo="Mensagem original de teste para a Fase 3",
        dataEnvio=datetime.utcnow()
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)

    yield msg

    # Teardown / Limpeza
    db_session.query(Mensagem).filter(Mensagem.id == msg.id).delete()
    db_session.commit()


# =====================================================================
# 1. TESTES DE EDIÇÃO DE MENSAGEM (PATCH /chat/mensagens/{id})
# =====================================================================

def test_1_1_editar_mensagem_propria_sucesso_dentro_15_min(client, db_session, setup_chat, mensagem_teste):
    """
    Teste 1.1: Sucesso ao editar mensagem própria dentro da janela de 15 minutos.
    Retorna status 200, texto atualizado e campo editado_em preenchido.
    """
    headers_a = setup_chat["headers_a"]
    novo_texto = "Texto da mensagem atualizado com sucesso dentro dos 15 minutos!"

    response = client.patch(
        f"/chat/mensagens/{mensagem_teste.id}",
        json={"conteudo": novo_texto},
        headers=headers_a
    )

    assert response.status_code == 200, f"Falha na edição: {response.text}"
    dados = response.json()
    assert dados["conteudo"] == novo_texto
    assert dados["editado_em"] is not None
    assert dados["id"] == mensagem_teste.id

    # Verificação direta de persistência no PostgreSQL
    db_session.expire_all()
    msg_db = db_session.query(Mensagem).filter(Mensagem.id == mensagem_teste.id).first()
    assert msg_db is not None
    assert msg_db.conteudo == novo_texto
    assert msg_db.editado_em is not None


def test_1_2_editar_mensagem_outro_usuario_retorna_403(client, setup_chat, mensagem_teste):
    """
    Teste 1.2: Erro 403 se outro usuário tentar editar mensagem que não foi ele quem enviou,
    e erro 401/403 caso a requisição não envie token de autenticação.
    """
    headers_b = setup_chat["headers_b"]  # user_b tenta editar a mensagem do user_a

    response_403 = client.patch(
        f"/chat/mensagens/{mensagem_teste.id}",
        json={"conteudo": "Tentativa indevida de alterar mensagem alheia"},
        headers=headers_b
    )
    assert response_403.status_code == 403
    assert "próprias mensagens" in response_403.json().get("detail", "")

    # Tentativa sem autenticação (401 ou 403 retornado pelo auth middleware)
    response_unauth = client.patch(
        f"/chat/mensagens/{mensagem_teste.id}",
        json={"conteudo": "Tentativa sem token"}
    )
    assert response_unauth.status_code in (401, 403)



def test_1_3_editar_mensagem_apos_15_minutos_retorna_400(client, db_session, setup_chat, mensagem_teste):
    """
    Teste 1.3: Erro 400 se a mensagem foi enviada há mais de 15 minutos
    (simulando dataEnvio com 16 minutos no passado).
    """
    headers_a = setup_chat["headers_a"]

    # Simula envio há 16 minutos
    dezesseis_min_atras = datetime.utcnow() - timedelta(minutes=16)
    mensagem_teste.dataEnvio = dezesseis_min_atras
    db_session.commit()
    db_session.refresh(mensagem_teste)

    response = client.patch(
        f"/chat/mensagens/{mensagem_teste.id}",
        json={"conteudo": "Tentando editar após a janela limite de 15 minutos"},
        headers=headers_a
    )

    assert response.status_code == 400
    assert "15 minutos" in response.json().get("detail", "")


# =====================================================================
# 2. TESTES DE EXCLUSÃO SEGURA / SOFT DELETE (DELETE /chat/mensagens/{id})
# =====================================================================

def test_2_1_soft_delete_mensagem_sucesso_retorna_200(client, setup_chat, mensagem_teste):
    """
    Teste 2.1: Sucesso ao solicitar exclusão da mensagem pelo remetente (retorno 200 OK).
    """
    headers_a = setup_chat["headers_a"]

    response = client.delete(
        f"/chat/mensagens/{mensagem_teste.id}",
        headers=headers_a
    )

    assert response.status_code == 200
    dados = response.json()
    assert dados.get("mensagem_id") == mensagem_teste.id
    assert dados.get("deletado_em") is not None


def test_2_2_soft_delete_persistencia_no_banco_deletado_em_e_deletado_por_id(client, db_session, setup_chat, mensagem_teste):
    """
    Teste 2.2: Confirma que o registro da mensagem AINDA EXISTE na tabela 'mensagem'
    do PostgreSQL (soft delete), com 'deletado_em' preenchido e 'deletado_por_id' igual ao ID do autor.
    """
    headers_a = setup_chat["headers_a"]
    user_a = setup_chat["user_a"]

    # Executa a exclusão lógica via API
    response = client.delete(f"/chat/mensagens/{mensagem_teste.id}", headers=headers_a)
    assert response.status_code == 200

    # Consulta direta no banco de dados
    db_session.expire_all()
    msg_db = db_session.query(Mensagem).filter(Mensagem.id == mensagem_teste.id).first()

    # O registro DEVE continuar existindo no PostgreSQL (não pode ter sido excluído com DELETE SQL)
    assert msg_db is not None, "A mensagem foi removida fisicamente do banco de dados em vez de receber soft delete!"
    assert msg_db.deletado_em is not None, "O campo deletado_em não foi gravado no banco!"
    assert msg_db.deletado_por_id == user_a.id, f"deletado_por_id incorreto: esperado {user_a.id}, obtido {msg_db.deletado_por_id}"


def test_2_3_soft_delete_usuario_nao_participante_retorna_403(client, db_session, setup_chat, mensagem_teste):
    """
    Teste 2.3: Impede que um usuário que não participa da conversa delete a mensagem.
    """
    headers_c = setup_chat["headers_c"]

    response = client.delete(
        f"/chat/mensagens/{mensagem_teste.id}",
        headers=headers_c
    )

    assert response.status_code == 403
    assert "permissão" in response.json().get("detail", "").lower()

    # Confirma que a mensagem permanece intacta no banco
    db_session.expire_all()
    msg_db = db_session.query(Mensagem).filter(Mensagem.id == mensagem_teste.id).first()
    assert msg_db.deletado_em is None, "A mensagem não deveria ter sido marcada como deletada por um terceiro!"


# =====================================================================
# 3. TESTES DO SISTEMA DE DENÚNCIAS (POST /chat/denuncias)
# =====================================================================

def test_3_1_denunciar_chat_sucesso_retorna_201(client, db_session, setup_chat):
    """
    Teste 3.1: Envio bem-sucedido de denúncia com payload completo, retornando 201 Created.
    """
    headers_a = setup_chat["headers_a"]
    user_a = setup_chat["user_a"]
    user_b = setup_chat["user_b"]
    conversa = setup_chat["conversa"]

    payload = {
        "denunciado_id": user_b.id,
        "conversa_id": conversa.id,
        "motivo": "Golpe / Fraude Financeira",
        "descricao": "Usuário solicitou pagamento externo por fora da plataforma Artfolio."
    }

    response = client.post("/chat/denuncias", json=payload, headers=headers_a)

    assert response.status_code == 201, f"Erro ao criar denúncia: {response.text}"
    dados = response.json()
    assert dados["denunciante_id"] == user_a.id
    assert dados["denunciado_id"] == user_b.id
    assert dados["conversa_id"] == conversa.id
    assert dados["motivo"] == payload["motivo"]
    assert dados["descricao"] == payload["descricao"]
    assert dados["status"] == "pendente"
    assert dados["id"] is not None

    # Limpeza da denúncia criada
    db_session.query(DenunciaChat).filter(DenunciaChat.id == dados["id"]).delete()
    db_session.commit()


def test_3_2_denunciar_chat_persistencia_no_banco_status_pendente(client, db_session, setup_chat):
    """
    Teste 3.2: Verificação no banco: confirmar que a denúncia foi persistida na tabela
    'denuncia_chat' com status 'pendente' e dados relacionais corretos.
    """
    headers_a = setup_chat["headers_a"]
    user_a = setup_chat["user_a"]
    user_b = setup_chat["user_b"]
    conversa = setup_chat["conversa"]

    payload = {
        "denunciado_id": user_b.id,
        "conversa_id": conversa.id,
        "motivo": "Linguagem Ofensiva / Assédio",
        "descricao": "Envio de mensagens com ofensas graves na conversa."
    }

    response = client.post("/chat/denuncias", json=payload, headers=headers_a)
    assert response.status_code == 201
    denuncia_id = response.json()["id"]

    # Consulta direta na tabela denuncia_chat
    db_session.expire_all()
    denuncia_db = db_session.query(DenunciaChat).filter(DenunciaChat.id == denuncia_id).first()

    assert denuncia_db is not None, "Denúncia não foi persistida na tabela denuncia_chat!"
    assert denuncia_db.denunciante_id == user_a.id
    assert denuncia_db.denunciado_id == user_b.id
    assert denuncia_db.conversa_id == conversa.id
    assert denuncia_db.motivo == payload["motivo"]
    assert denuncia_db.descricao == payload["descricao"]
    assert denuncia_db.status == "pendente"
    assert denuncia_db.criado_em is not None

    # Limpeza
    db_session.query(DenunciaChat).filter(DenunciaChat.id == denuncia_id).delete()
    db_session.commit()


def test_3_3_denunciar_chat_campos_obrigatorios_ausentes_retorna_422(client, setup_chat):
    """
    Teste 3.3: Erro 422 Unprocessable Entity se campos obrigatórios (como motivo,
    denunciado_id ou conversa_id) não forem informados.
    """
    headers_a = setup_chat["headers_a"]
    user_b = setup_chat["user_b"]
    conversa = setup_chat["conversa"]

    # 1. Sem 'motivo'
    res_sem_motivo = client.post("/chat/denuncias", json={
        "denunciado_id": user_b.id,
        "conversa_id": conversa.id,
        "descricao": "Sem motivo especificado"
    }, headers=headers_a)
    assert res_sem_motivo.status_code == 422

    # 2. Sem 'denunciado_id'
    res_sem_denunciado = client.post("/chat/denuncias", json={
        "conversa_id": conversa.id,
        "motivo": "Spam / Outro"
    }, headers=headers_a)
    assert res_sem_denunciado.status_code == 422

    # 3. Sem 'conversa_id'
    res_sem_conversa = client.post("/chat/denuncias", json={
        "denunciado_id": user_b.id,
        "motivo": "Spam / Outro"
    }, headers=headers_a)
    assert res_sem_conversa.status_code == 422


def test_3_4_denunciar_chat_auto_denuncia_retorna_400(client, setup_chat):
    """
    Teste 3.4 (Segurança adicional): Bloqueio de auto-denúncia (denunciante_id == denunciado_id).
    Retorna 400 Bad Request.
    """
    headers_a = setup_chat["headers_a"]
    user_a = setup_chat["user_a"]
    conversa = setup_chat["conversa"]

    payload = {
        "denunciado_id": user_a.id,  # O próprio usuário
        "conversa_id": conversa.id,
        "motivo": "Spam / Outro"
    }

    response = client.post("/chat/denuncias", json=payload, headers=headers_a)
    assert response.status_code == 400
    assert "não pode denunciar a si mesmo" in response.json().get("detail", "").lower()


def test_3_5_denunciar_chat_usuario_nao_participante_retorna_403(client, setup_chat):
    """
    Teste 3.5 (Segurança adicional): Impede que usuário externo à conversa registre denúncia sobre ela.
    Retorna 403 Forbidden.
    """
    headers_c = setup_chat["headers_c"]
    user_b = setup_chat["user_b"]
    conversa = setup_chat["conversa"]

    payload = {
        "denunciado_id": user_b.id,
        "conversa_id": conversa.id,
        "motivo": "Spam / Outro"
    }

    response = client.post("/chat/denuncias", json=payload, headers=headers_c)
    assert response.status_code == 403
    assert "participa" in response.json().get("detail", "").lower()
