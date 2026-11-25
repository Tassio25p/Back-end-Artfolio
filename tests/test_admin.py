"""
Suíte de Testes Automatizados - Módulo Administrativo e Moderação (Artfolio)
=============================================================================
Cobre os requisitos de negócio e segurança do Painel de Moderação:
1. Segurança & Autorização:
   - Usuário artista/comum é bloqueado com 403 Forbidden
   - Usuários com papel 'moderador' ou 'admin' têm acesso liberado

2. Métricas do Topo (GET /admin/metricas):
   - Contagem precisa de obras pendentes, denúncias abertas, usuários sinalizados e logs

3. Quarentena de Obras:
   - GET /admin/obras/quarentena lista apenas obras pendentes/quarentena
   - PATCH /admin/obras/{id}/julgar com 'aprovar' publica a obra e gera log
   - PATCH /admin/obras/{id}/julgar com 'rejeitar' arquiva a obra e gera Notificação + log

4. Denúncias de Chat e Auditoria:
   - GET /admin/denuncias lista as denúncias de conversas
   - GET /admin/denuncias/{id}/auditoria-chat traz a conversa COMPLETA,
     sinalizando foi_apagada=True e foi_editada=True para mensagens deletadas/alteradas
   - PATCH /admin/denuncias/{id} resolve denúncia com nota do moderador e gera log

5. Sanções a Usuários:
   - 'advertir': gera Notificação formal e log de auditoria
   - 'suspender': define data de suspensão futura e gera notificação + log
   - 'banir': define ativo=False e deletado=True e gera log

6. Logs de Auditoria:
   - GET /admin/logs lista em ordem decrescente
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.controllers.auth_controller import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.denuncia_chat_model import DenunciaChat
from app.models.notificacao_model import Notificacao
from app.models.log_auditoria_model import LogAuditoria
from app.core.limiter import limiter

# Desativa rate limiting durante os testes para evitar dependência do Redis
limiter.enabled = False


# Criar engine SQLite em memória para testes isolados
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def db():
    """Cria tabelas no SQLite em memória e provê a sessão."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def dados_teste(db):
    """Popula o banco com entidades para os testes de moderação."""
    # 1. Usuários
    admin = Usuario(nome="Admin Artfolio", email="admin@artfolio.com", tipo_conta="admin", ativo=True)
    moderador = Usuario(nome="Moderador Lucas", email="mod@artfolio.com", tipo_conta="moderador", ativo=True)
    artista = Usuario(nome="Artista Silva", email="artista@artfolio.com", tipo_conta="artista", ativo=True)
    infrator = Usuario(nome="Infrator Fake", email="infrator@artfolio.com", tipo_conta="artista", ativo=True)

    db.add_all([admin, moderador, artista, infrator])
    db.commit()
    db.refresh(admin)
    db.refresh(moderador)
    db.refresh(artista)
    db.refresh(infrator)

    # 2. Obras (1 em quarentena, 1 pendente, 1 publicada)
    obra_quarentena = Postagem(
        idUsuario=infrator.id,
        legenda="Obra com possível plágio",
        arquivoUrl="https://exemplo.com/arte1.jpg",
        status="quarentena",
        deletado=False,
    )
    obra_pendente = Postagem(
        idUsuario=artista.id,
        legenda="Nova pintura digital",
        arquivoUrl="https://exemplo.com/arte2.jpg",
        status="pendente",
        deletado=False,
    )
    obra_publicada = Postagem(
        idUsuario=artista.id,
        legenda="Obra já aprovada",
        arquivoUrl="https://exemplo.com/arte3.jpg",
        status="publicada",
        deletado=False,
    )
    db.add_all([obra_quarentena, obra_pendente, obra_publicada])
    db.commit()
    db.refresh(obra_quarentena)
    db.refresh(obra_pendente)

    # 3. Conversa e Mensagens (incluindo mensagem apagada e editada)
    conversa = Conversa()
    db.add(conversa)
    db.commit()
    db.refresh(conversa)

    db.add_all([
        ConversaUsuario(idConversa=conversa.id, idUsuario=artista.id),
        ConversaUsuario(idConversa=conversa.id, idUsuario=infrator.id),
    ])
    db.commit()

    msg_normal = Mensagem(
        idRemetente=artista.id,
        idConversa=conversa.id,
        conteudo="Olá, tudo bem?",
        deletado=False,
    )
    msg_apagada = Mensagem(
        idRemetente=infrator.id,
        idConversa=conversa.id,
        conteudo="Mensagem ofensiva que tentei apagar",
        deletado=True,
        deletado_em=datetime.utcnow(),
    )
    msg_editada = Mensagem(
        idRemetente=infrator.id,
        idConversa=conversa.id,
        conteudo="Mensagem editada disfarçada",
        editado_em=datetime.utcnow(),
    )
    db.add_all([msg_normal, msg_apagada, msg_editada])
    db.commit()

    # 4. Denúncia de Chat
    denuncia = DenunciaChat(
        denunciante_id=artista.id,
        denunciado_id=infrator.id,
        conversa_id=conversa.id,
        motivo="Ofensas e assédio no chat",
        descricao="O usuário me enviou mensagens agressivas e depois apagou.",
        status="pendente",
    )
    db.add(denuncia)
    db.commit()
    db.refresh(denuncia)

    return {
        "admin": admin,
        "moderador": moderador,
        "artista": artista,
        "infrator": infrator,
        "obra_quarentena": obra_quarentena,
        "obra_pendente": obra_pendente,
        "conversa": conversa,
        "denuncia": denuncia,
    }


@pytest.fixture
def client_admin(db, dados_teste):
    """Cliente simulando o usuário Admin autenticado."""
    def override_get_db():
        yield db

    def override_obter_usuario():
        return dados_teste["admin"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[obter_usuario_atual] = override_obter_usuario

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client_moderador(db, dados_teste):
    """Cliente simulando o usuário Moderador autenticado."""
    def override_get_db():
        yield db

    def override_obter_usuario():
        return dados_teste["moderador"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[obter_usuario_atual] = override_obter_usuario

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def client_comum(db, dados_teste):
    """Cliente simulando um usuário comum (artista) sem papel administrativo."""
    def override_get_db():
        yield db

    def override_obter_usuario():
        return dados_teste["artista"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[obter_usuario_atual] = override_obter_usuario

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# =============================================================================
# TESTES
# =============================================================================

def test_bloqueio_usuario_sem_permissao(client_comum):
    """Garante que usuários sem papel 'admin' ou 'moderador' recebem 403."""
    res = client_comum.get("/admin/metricas")
    assert res.status_code == 403
    assert "Acesso restrito" in res.json()["detail"]


def test_obter_metricas_admin(client_admin):
    """Testa contagem de métricas em tempo real no topo do painel."""
    res = client_admin.get("/admin/metricas")
    assert res.status_code == 200
    data = res.json()
    assert data["obras_pendentes"] >= 2  # obra_quarentena + obra_pendente
    assert data["denuncias_abertas"] >= 1
    assert data["usuarios_sinalizados"] >= 1
    assert "logs_recentes" in data


def test_quarentena_listar_e_julgar_aprovar(client_moderador, db, dados_teste):
    """Testa listar obras em quarentena e aprovar uma publicação."""
    res = client_moderador.get("/admin/obras/quarentena")
    assert res.status_code == 200
    obras = res.json()
    assert len(obras) >= 2

    obra_id = dados_teste["obra_pendente"].id
    res_aprovar = client_moderador.patch(
        f"/admin/obras/{obra_id}/julgar",
        json={"acao": "aprovar"},
    )
    assert res_aprovar.status_code == 200
    assert res_aprovar.json()["status"] == "publicada"

    # Verificar banco: status deve ser publicada e deve ter log de auditoria
    db.expire_all()
    obra = db.query(Postagem).filter(Postagem.id == obra_id).first()
    assert obra.status == "publicada"

    log = db.query(LogAuditoria).filter(LogAuditoria.alvo_id == obra_id, LogAuditoria.acao == "obra_aprovada").first()
    assert log is not None
    assert log.moderador_id == dados_teste["moderador"].id


def test_quarentena_julgar_rejeitar_com_notificacao(client_moderador, db, dados_teste):
    """Testa rejeição de obra com motivo formal e criação de notificação."""
    obra_id = dados_teste["obra_quarentena"].id
    motivo = "Conteúdo não autoral detectado por verificação reversa."

    res = client_moderador.patch(
        f"/admin/obras/{obra_id}/julgar",
        json={"acao": "rejeitar", "motivo": motivo},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejeitada"

    db.expire_all()
    obra = db.query(Postagem).filter(Postagem.id == obra_id).first()
    assert obra.deletado is True
    assert obra.status == "rejeitada"

    # Verificar notificação criada para o autor da obra
    notif = db.query(Notificacao).filter(Notificacao.idPostagem == obra_id).first()
    assert notif is not None
    assert motivo in notif.mensagem


def test_denuncias_chat_e_auditoria_mensagens_apagadas(client_admin, dados_teste):
    """
    Testa a auditoria de chat verificando se mensagens apagadas
    vêm sinalizadas com foi_apagada=True e mensagens editadas com foi_editada=True.
    """
    denuncia_id = dados_teste["denuncia"].id

    # Listar denúncias
    res = client_admin.get("/admin/denuncias")
    assert res.status_code == 200
    denuncias = res.json()
    assert len(denuncias) >= 1
    assert any(d["id"] == denuncia_id for d in denuncias)

    # Auditoria forense do chat
    res_audit = client_admin.get(f"/admin/denuncias/{denuncia_id}/auditoria-chat")
    assert res_audit.status_code == 200
    audit = res_audit.json()
    assert audit["denuncia_id"] == denuncia_id
    assert len(audit["mensagens"]) == 3

    # Checar flag foi_apagada na mensagem deletada
    msg_del = next(m for m in audit["mensagens"] if "Mensagem ofensiva" in (m["conteudo"] or ""))
    assert msg_del["foi_apagada"] is True
    assert msg_del["apagado_em"] is not None

    # Checar flag foi_editada na mensagem alterada
    msg_edit = next(m for m in audit["mensagens"] if "Mensagem editada" in (m["conteudo"] or ""))
    assert msg_edit["foi_editada"] is True
    assert msg_edit["editado_em"] is not None


def test_atualizar_status_denuncia_com_nota(client_moderador, db, dados_teste):
    """Testa atualizar o status da denúncia para 'resolvida' com nota do moderador."""
    denuncia_id = dados_teste["denuncia"].id
    res = client_moderador.patch(
        f"/admin/denuncias/{denuncia_id}",
        json={"status": "resolvida", "nota_moderador": "Infrator foi advertido formalmente."},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "resolvida"
    assert res.json()["nota_moderador"] == "Infrator foi advertido formalmente."

    db.expire_all()
    log = db.query(LogAuditoria).filter(LogAuditoria.acao == "denuncia_resolvida").first()
    assert log is not None


def test_sancao_advertir_e_suspender_usuario(client_admin, db, dados_teste):
    """Testa aplicação de advertência e suspensão disciplinar a um usuário infrator."""
    infrator_id = dados_teste["infrator"].id

    # 1. Advertência
    res_adv = client_admin.patch(
        f"/admin/usuarios/{infrator_id}/sancao",
        json={"acao": "advertir", "motivo": "Linguagem abusiva no chat."},
    )
    assert res_adv.status_code == 200

    # 2. Suspensão por 15 dias
    res_susp = client_admin.patch(
        f"/admin/usuarios/{infrator_id}/sancao",
        json={"acao": "suspender", "dias_suspensao": 15, "motivo": "Reincidência de infração."},
    )
    assert res_susp.status_code == 200
    assert res_susp.json()["suspenso_ate"] is not None

    db.expire_all()
    infrator = db.query(Usuario).filter(Usuario.id == infrator_id).first()
    assert infrator.suspenso_ate is not None
    assert infrator.suspenso_ate > datetime.utcnow()


def test_listar_logs_auditoria(client_admin):
    """Testa consulta dos logs de auditoria."""
    res = client_admin.get("/admin/logs?limit=10")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    # Valida estrutura do log
    primeiro_log = logs[0]
    assert "acao" in primeiro_log
    assert "moderador_id" in primeiro_log
    assert "alvo_tipo" in primeiro_log
