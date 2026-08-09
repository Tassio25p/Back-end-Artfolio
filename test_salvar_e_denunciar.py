import sys
from fastapi import HTTPException
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
from app.models.obra_salva_model import ObraSalva
from app.models.denuncia_model import Denuncia

from app.services.obra_salva_service import ObraSalvaService
from app.services.denuncia_service import DenunciaService
from app.services.postagem_service import PostagemService
from app.schemas.postagem_schema import PostagemCriar
from app.schemas.denuncia_schema import DenunciaCriar, DenunciaAtualizarStatus

def testar_salvar_e_denunciar():
    print("=== ARTFOLIO BACKEND: BATERIA COMPLETA DE TESTES DE SALVAR E DENUNCIAR OBRAS ===\n")

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # 1. Preparar contas de teste
        print("[1/7] Preparando contas de teste (Usuário A, Usuário B e Admin)...")
        usr_a = db.query(Usuario).filter(Usuario.email == "usr_a_save@artfolio.com").first()
        if not usr_a:
            usr_a = Usuario(
                nome="Usuário A (Salvador)",
                email="usr_a_save@artfolio.com",
                senha="hash_user_a",
                cpf="77777777777",
                tipo_conta="artista"
            )
            db.add(usr_a)
            db.commit()
            db.refresh(usr_a)

        usr_b = db.query(Usuario).filter(Usuario.email == "usr_b_save@artfolio.com").first()
        if not usr_b:
            usr_b = Usuario(
                nome="Usuário B (Autor)",
                email="usr_b_save@artfolio.com",
                senha="hash_user_b",
                cpf="88888888888",
                tipo_conta="artista"
            )
            db.add(usr_b)
            db.commit()
            db.refresh(usr_b)

        admin = db.query(Usuario).filter(Usuario.email == "admin_mod@artfolio.com").first()
        if not admin:
            admin = Usuario(
                nome="Admin Modos",
                email="admin_mod@artfolio.com",
                senha="hash_admin",
                cpf="99999999999",
                tipo_conta="admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        cat = db.query(Categoria).first()
        if not cat:
            cat = Categoria(nomeCategoria="Arte Teste Salvar")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        post_b = PostagemService.criar_postagem(
            db, usr_b.id, PostagemCriar(idCategoria=cat.id, legenda="Obra de B para testes de salvar e denunciar", arquivoUrl="http://artfolio.com/post_b.jpg")
        )

        # Limpar registros prévios
        db.query(ObraSalva).filter(ObraSalva.idPostagem == post_b.id).delete()
        db.query(Denuncia).filter(Denuncia.idPostagem == post_b.id).delete()
        db.commit()
        print(f"  [OK] Usuário A (ID {usr_a.id}), Usuário B (ID {usr_b.id}), Admin (ID {admin.id}) e Obra (ID {post_b.id}) prontos.")

        # ----------------------------------------------------
        # TESTE 1: Salvar Obra (A salva obra de B)
        # ----------------------------------------------------
        print("\n[2/7] TESTE 1: Usuário A salva a obra de B...")
        salva_obj = ObraSalvaService.salvar_obra(db, usr_a.id, post_b.id)
        assert salva_obj.idUsuario == usr_a.id
        assert salva_obj.idPostagem == post_b.id

        status_a = ObraSalvaService.checar_salvo(db, usr_a.id, post_b.id)
        assert status_a["salvo"] == True
        print("  [OK] Obra salva com sucesso no PostgreSQL! checar_salvo retornou salvo=True.")

        # ----------------------------------------------------
        # TESTE 2: Prevenção de duplicidade ao salvar
        # ----------------------------------------------------
        print("\n[3/7] TESTE 2: Testando prevenção de duplicidade de salvamento...")
        try:
            ObraSalvaService.salvar_obra(db, usr_a.id, post_b.id)
            print("  [ERRO] O sistema permitiu salvar a mesma obra duas vezes!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 400
            print(f"  [OK] Duplicidade de salvamento bloqueada (HTTP {e.status_code}: '{e.detail}')")

        # ----------------------------------------------------
        # TESTE 3: Isolamento por conta (B não vê obra como salva)
        # ----------------------------------------------------
        print("\n[4/7] TESTE 3: Verificando isolamento de conta (Obra não deve estar salva para B)...")
        status_b = ObraSalvaService.checar_salvo(db, usr_b.id, post_b.id)
        assert status_b["salvo"] == False

        lista_salvas_a = ObraSalvaService.listar_salvas(db, usr_a.id)
        assert any(p.id == post_b.id for p in lista_salvas_a)
        print("  [OK] Isolamento de sessão validado! Lista de salvos de A contém a obra e B enxerga salvo=False.")

        # ----------------------------------------------------
        # TESTE 4: Denunciar Obra (A denuncia obra de B)
        # ----------------------------------------------------
        print("\n[5/7] TESTE 4: Usuário A denuncia a obra de B...")
        denuncia_dados = DenunciaCriar(
            motivo="Plágio ou obra copiada",
            descricao="Cópia de imagem protegida por direitos autorais"
        )
        denuncia_obj = DenunciaService.criar_denuncia(db, usr_a.id, post_b.id, denuncia_dados)
        assert denuncia_obj.idUsuario == usr_a.id
        assert denuncia_obj.idPostagem == post_b.id
        assert denuncia_obj.status == "PENDENTE"
        print(f"  [OK] Denúncia criada com sucesso! ID {denuncia_obj.id} | Motivo: '{denuncia_obj.motivo}' | Status: '{denuncia_obj.status}'")

        # ----------------------------------------------------
        # TESTE 5: Impedimento de Auto-Denúncia e Duplicidade
        # ----------------------------------------------------
        print("\n[6/7] TESTE 5: Testando impedimento de auto-denúncia e denúncia duplicada...")
        # Auto-denúncia
        try:
            DenunciaService.criar_denuncia(db, usr_b.id, post_b.id, denuncia_dados)
            print("  [ERRO] O sistema permitiu que o autor denunciasse a própria obra!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 400
            print(f"  [OK] Auto-denúncia bloqueada (HTTP {e.status_code}: '{e.detail}')")

        # Duplicidade
        try:
            DenunciaService.criar_denuncia(db, usr_a.id, post_b.id, denuncia_dados)
            print("  [ERRO] O sistema permitiu denúncia duplicada!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 400
            print(f"  [OK] Denúncia duplicada bloqueada (HTTP {e.status_code}: '{e.detail}')")

        # ----------------------------------------------------
        # TESTE 6: Moderação no Painel Admin
        # ----------------------------------------------------
        print("\n[7/7] TESTE 6: Listando e atualizando denúncias no painel de moderação...")
        denuncias_admin = DenunciaService.listar_denuncias(db, admin.tipo_conta)
        denuncia_item = next((d for d in denuncias_admin if d.id == denuncia_obj.id), None)
        assert denuncia_item is not None

        # Atualizar status para RESOLVIDA
        denuncia_atualizada = DenunciaService.atualizar_status(
            db, denuncia_obj.id, DenunciaAtualizarStatus(status="RESOLVIDA"), admin.tipo_conta
        )
        assert denuncia_atualizada.status == "RESOLVIDA"
        print(f"  [OK] Status da denúncia atualizado para '{denuncia_atualizada.status}' com sucesso!")

        # Desfazer salvamento de teste
        ObraSalvaService.remover_salvo(db, usr_a.id, post_b.id)
        assert ObraSalvaService.checar_salvo(db, usr_a.id, post_b.id)["salvo"] == False
        print("  [OK] Remoção dos salvos validada com sucesso.")

        # Limpeza
        db.query(Denuncia).filter(Denuncia.id == denuncia_obj.id).delete()
        PostagemService.deletar_postagem(db, post_b.id, usr_b.id)
        db.commit()

        print("\n=== TODOS OS TESTES DE SALVAR OBRA E DENUNCIAR OBRA PASSARAM COM SUCESSO! ===")

    except Exception as e:
        print(f"\n[ERRO FATAL NOS TESTES]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    testar_salvar_e_denunciar()
