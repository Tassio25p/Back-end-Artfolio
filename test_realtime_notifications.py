import sys
from app.database import SessionLocal, engine, Base
from app.models.usuario_model import Usuario
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.assistente_conversa_model import AssistenteConversa
from app.models.assistente_mensagem_model import AssistenteMensagem
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.seguidor_model import Seguidor
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao

from app.services.seguidor_service import SeguidorService
from app.services.comentario_service import ComentarioService
from app.services.postagem_service import PostagemService
from app.services.notificacao_service import NotificacaoService
from app.schemas.comentario_schema import ComentarioCriar
from app.schemas.postagem_schema import PostagemCriar

def testar_realtime_notificacoes():
    print("=== ARTFOLIO BACKEND: TESTE DO CONTADOR E ESTADO DE NOTIFICAÇÕES EM TEMPO REAL ===\n")

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # 1. Obter/Criar Usuários A e B
        usr_a = db.query(Usuario).filter(Usuario.email == "user_a_rt@artfolio.com").first()
        if not usr_a:
            usr_a = Usuario(
                nome="Usuário A (Realtime)",
                email="user_a_rt@artfolio.com",
                senha="hash_rt_a",
                cpf="55555555555",
                tipo_conta="artista"
            )
            db.add(usr_a)
            db.commit()
            db.refresh(usr_a)

        usr_b = db.query(Usuario).filter(Usuario.email == "user_b_rt@artfolio.com").first()
        if not usr_b:
            usr_b = Usuario(
                nome="Usuário B (Realtime)",
                email="user_b_rt@artfolio.com",
                senha="hash_rt_b",
                cpf="66666666666",
                tipo_conta="artista"
            )
            db.add(usr_b)
            db.commit()
            db.refresh(usr_b)

        cat = db.query(Categoria).first()
        if not cat:
            cat = Categoria(nomeCategoria="Categoria Realtime")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        post_b = PostagemService.criar_postagem(
            db, usr_b.id, PostagemCriar(idCategoria=cat.id, legenda="Post Realtime de B", arquivoUrl="http://artfolio.com/rt.jpg")
        )

        # Limpar notificações prévias para teste limpo
        NotificacaoService.marcar_todas_como_lidas(db, usr_b.id)
        NotificacaoService.marcar_todas_como_lidas(db, usr_a.id)

        # 2. Verificar contagem inicial de não lidas para B (deve ser 0)
        c0 = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"[Passo 1] Contagem inicial de não lidas para Usuário B: {c0}")

        # 3. Usuário A segue B -> Contagem deve incrementar imediatamente para 1
        if SeguidorService.obter_status_relacionamento(db, usr_a.id, usr_b.id).seguindo:
            SeguidorService.deixar_de_seguir(db, usr_a.id, usr_b.id)

        SeguidorService.seguir(db, usr_a.id, usr_b.id)
        c1 = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"[Passo 2] Usuário A seguiu B -> Nova contagem de não lidas para B: {c1}")
        assert c1 == c0 + 1, f"Esperado {c0 + 1}, obtido {c1}"

        # 4. Usuário A comenta na obra de B -> Contagem deve incrementar para 2
        comentario_rt = ComentarioService.criar_comentario(db, usr_a.id, post_b.id, ComentarioCriar(conteudo="Comentário em tempo real"))
        c2 = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"[Passo 3] Usuário A comentou na obra de B -> Nova contagem de não lidas para B: {c2}")
        assert c2 == c1 + 1, f"Esperado {c1 + 1}, obtido {c2}"

        # 5. Usuário B marca 1 notificação como lida -> Contagem deve decrementar para 1
        notifs_b = NotificacaoService.listar_notificacoes(db, usr_b.id)
        notif_para_ler = next(n for n in notifs_b if not n.lida)
        NotificacaoService.marcar_como_lida(db, usr_b.id, notif_para_ler.id)
        c3 = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"[Passo 4] Usuário B leu 1 notificação -> Nova contagem para B: {c3}")
        assert c3 == c2 - 1, f"Esperado {c2 - 1}, obtido {c3}"

        # 6. Usuário B marca todas como lidas -> Contagem cai para 0
        NotificacaoService.marcar_todas_como_lidas(db, usr_b.id)
        c4 = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"[Passo 5] Usuário B marcou todas como lidas -> Nova contagem para B: {c4}")
        assert c4 == 0, f"Esperado 0, obtido {c4}"

        # 7. Isolamento de sessão (Contagem de A deve ser independente da contagem de B)
        cA = NotificacaoService.contar_nao_lidas(db, usr_a.id)
        print(f"[Passo 6] Contagem de não lidas do Usuário A: {cA}")
        assert cA == 0, "Usuário A não deve possuir notificações de B"

        # Limpeza
        ComentarioService.deletar_comentario(db, usr_a.id, comentario_rt.id, "cliente")
        PostagemService.deletar_postagem(db, post_b.id, usr_b.id)
        SeguidorService.deixar_de_seguir(db, usr_a.id, usr_b.id)

        print("\n=== TODOS OS TESTES DE CONTADOR EM TEMPO REAL PASSARAM COM SUCESSO! ===")

    except Exception as e:
        print(f"\n[ERRO FATAL NOS TESTES REALTIME]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    testar_realtime_notificacoes()
