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
from app.services.usuario_service import UsuarioService
from app.services.notificacao_service import NotificacaoService
from app.schemas.postagem_schema import PostagemCriar
from fastapi import HTTPException

def testar_seguidores_e_notificacoes():
    print("=== ARTFOLIO BACKEND: TESTE DO SISTEMA DE SEGUIDORES E NOTIFICAÇÕES ===\n")

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # 1. Criar ou buscar Usuário A e Usuário B para os testes
        print("[1/7] Preparando contas de teste (Usuário A e Usuário B)...")
        usr_a = db.query(Usuario).filter(Usuario.email == "usr_a_follow@artfolio.com").first()
        if not usr_a:
            usr_a = Usuario(
                nome="Usuário A (Tester)",
                email="usr_a_follow@artfolio.com",
                senha="hash_senha_test_a",
                cpf="11111111111",
                tipo_conta="artista",
                biografia="Perfil de teste A"
            )
            db.add(usr_a)
            db.commit()
            db.refresh(usr_a)

        usr_b = db.query(Usuario).filter(Usuario.email == "usr_b_follow@artfolio.com").first()
        if not usr_b:
            usr_b = Usuario(
                nome="Usuário B (Tester)",
                email="usr_b_follow@artfolio.com",
                senha="hash_senha_test_b",
                cpf="22222222222",
                tipo_conta="artista",
                biografia="Perfil de teste B"
            )
            db.add(usr_b)
            db.commit()
            db.refresh(usr_b)

        print(f"  [OK] Usuário A (ID {usr_a.id}) e Usuário B (ID {usr_b.id}) prontos.")

        # Limpar relacionamentos e notificações anteriores entre A e B
        db.query(Seguidor).filter(
            ((Seguidor.idSeguidor == usr_a.id) & (Seguidor.idSeguido == usr_b.id)) |
            ((Seguidor.idSeguidor == usr_b.id) & (Seguidor.idSeguido == usr_a.id))
        ).delete()
        db.query(Notificacao).filter(
            ((Notificacao.idUsuario == usr_a.id) & (Notificacao.idRemetente == usr_b.id)) |
            ((Notificacao.idUsuario == usr_b.id) & (Notificacao.idRemetente == usr_a.id))
        ).delete()
        db.commit()
        print("  [OK] Dados prévios de testes limpos.")

        # 2. Testar impedimento de seguir a si mesmo (A -> A)
        print("\n[2/7] Testando prevenção de auto-seguir (A -> A)...")
        try:
            SeguidorService.seguir(db, usr_a.id, usr_a.id)
            print("  [ERRO] O sistema permitiu que o usuário seguisse a si mesmo!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 400
            print(f"  [OK] Auto-seguir bloqueado com sucesso (HTTP {e.status_code}: '{e.detail}')")

        # 3. Usuário A segue B (A -> B)
        print("\n[3/7] Usuário A segue Usuário B (A -> B)...")
        rel_a_b = SeguidorService.seguir(db, usr_a.id, usr_b.id)
        assert rel_a_b.idSeguidor == usr_a.id
        assert rel_a_b.idSeguido == usr_b.id
        print("  [OK] Relacionamento (A -> B) registrado no PostgreSQL!")

        # 4. Verificar notificação gerada para B
        print("\n[4/7] Verificando notificação gerada para o Usuário B...")
        notifs_b = NotificacaoService.listar_notificacoes(db, usr_b.id)
        notif_follow_b = next((n for n in notifs_b if n.tipo == "FOLLOW" and n.idRemetente == usr_a.id), None)
        assert notif_follow_b is not None, "Usuário B deveria ter recebido uma notificação FOLLOW de A"
        assert f"{usr_a.nome} começou a seguir você." in notif_follow_b.mensagem
        print(f"  [OK] Notificação recebida por B: '{notif_follow_b.mensagem}'")

        # 5. Testar prevenção de duplicidade (A tenta seguir B novamente)
        print("\n[5/7] Testando prevenção de duplicidade (A tenta seguir B novamente)...")
        try:
            SeguidorService.seguir(db, usr_a.id, usr_b.id)
            print("  [ERRO] O sistema permitiu seguir duas vezes!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 400
            print(f"  [OK] Duplicidade barrada com sucesso (HTTP {e.status_code}: '{e.detail}')")

        # Verificar status de relacionamento antes de B seguir de volta
        status_a_para_b = SeguidorService.obter_status_relacionamento(db, usr_a.id, usr_b.id)
        assert status_a_para_b.seguindo == True
        assert status_a_para_b.seguidoresCount == 1

        status_b_para_a = SeguidorService.obter_status_relacionamento(db, usr_b.id, usr_a.id)
        assert status_b_para_a.seguindo == False
        assert status_b_para_a.segueDeVolta == True  # B vê "Seguir de volta"

        print("  [OK] Status de relacionamento verificado: B enxerga opção 'Seguir de volta'!")

        # 6. Usuário B clica 'Seguir de volta' (B -> A)
        print("\n[6/7] Usuário B segue A de volta (B -> A)...")
        rel_b_a = SeguidorService.seguir(db, usr_b.id, usr_a.id)
        assert rel_b_a.idSeguidor == usr_b.id

        # Verificar se notificação foi enviada para A
        notifs_a = NotificacaoService.listar_notificacoes(db, usr_a.id)
        notif_follow_a = next((n for n in notifs_a if n.tipo == "FOLLOW" and n.idRemetente == usr_b.id), None)
        assert notif_follow_a is not None, "Usuário A deveria ter recebido notificação FOLLOW de B"
        print(f"  [OK] Notificação enviada para A: '{notif_follow_a.mensagem}'")

        # Ambos os status devem mostrar 'seguindo = True'
        status_a_pos = SeguidorService.obter_status_relacionamento(db, usr_a.id, usr_b.id)
        status_b_pos = SeguidorService.obter_status_relacionamento(db, usr_b.id, usr_a.id)
        assert status_a_pos.seguindo == True
        assert status_b_pos.seguindo == True
        print("  [OK] Relacionamento bidirecional ativo! Ambos exibem 'Seguindo'.")

        # 7. Testar 'Deixar de seguir' (A deixa de seguir B)
        print("\n[7/7] Testando 'Deixar de seguir' (A deixa de seguir B)...")
        res_unfollow = SeguidorService.deixar_de_seguir(db, usr_a.id, usr_b.id)
        assert res_unfollow["message"] == "Você deixou de seguir este usuário."

        status_a_final = SeguidorService.obter_status_relacionamento(db, usr_a.id, usr_b.id)
        assert status_a_final.seguindo == False
        assert status_a_final.seguidoresCount == 0
        print("  [OK] Deixar de seguir executado e contadores atualizados!")

        print("\n=== TODOS OS TESTES DO SISTEMA DE SEGUIDORES E NOTIFICAÇÕES PASSARAM COM SUCESSO! ===")

    except Exception as e:
        print(f"\n[ERRO FATAL NOS TESTES]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    testar_seguidores_e_notificacoes()
