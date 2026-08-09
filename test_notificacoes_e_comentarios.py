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

from app.services.seguidor_service import SeguidorService
from app.services.usuario_service import UsuarioService
from app.services.comentario_service import ComentarioService
from app.services.postagem_service import PostagemService
from app.services.notificacao_service import NotificacaoService
from app.schemas.comentario_schema import ComentarioCriar, ComentarioResposta
from app.schemas.postagem_schema import PostagemCriar

def testar_notificacoes_e_comentarios():
    print("=== ARTFOLIO BACKEND: BATERIA COMPLETA DE TESTES DE NOTIFICAÇÕES E COMENTÁRIOS ===\n")

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # 1. Preparar Usuários e Postagem de Teste
        print("[1/8] Preparando usuários e postagem de teste...")
        usr_a = db.query(Usuario).filter(Usuario.email == "user_a_notif@artfolio.com").first()
        if not usr_a:
            usr_a = Usuario(
                nome="Usuário A (Comentador)",
                email="user_a_notif@artfolio.com",
                senha="hash_user_a",
                cpf="33333333333",
                tipo_conta="artista",
                biografia="Biografia do Usuário A"
            )
            db.add(usr_a)
            db.commit()
            db.refresh(usr_a)

        usr_b = db.query(Usuario).filter(Usuario.email == "user_b_notif@artfolio.com").first()
        if not usr_b:
            usr_b = Usuario(
                nome="Usuário B (Autor da Obra)",
                email="user_b_notif@artfolio.com",
                senha="hash_user_b",
                cpf="44444444444",
                tipo_conta="artista",
                biografia="Biografia do Usuário B"
            )
            db.add(usr_b)
            db.commit()
            db.refresh(usr_b)

        cat = db.query(Categoria).first()
        if not cat:
            cat = Categoria(nomeCategoria="Arte Digital Teste Notif")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        # Postagem pertencente ao Usuário B
        dados_post_b = PostagemCriar(
            idCategoria=cat.id,
            legenda="Obra de B para teste de comentários e notificações",
            arquivoUrl="https://artfolio.com.br/uploads/obra_b.jpg"
        )
        post_b = PostagemService.criar_postagem(db, usr_b.id, dados_post_b)

        # Postagem pertencente ao Usuário A (para teste de auto-comentário)
        dados_post_a = PostagemCriar(
            idCategoria=cat.id,
            legenda="Obra de A para teste de auto-comentário",
            arquivoUrl="https://artfolio.com.br/uploads/obra_a.jpg"
        )
        post_a = PostagemService.criar_postagem(db, usr_a.id, dados_post_a)

        print(f"  [OK] Usuário A (ID {usr_a.id}), Usuário B (ID {usr_b.id}), Obra de B (ID {post_b.id}) e Obra de A (ID {post_a.id}) prontos.")

        # Limpar notificações prévias entre A e B
        db.query(Notificacao).filter(
            ((Notificacao.idUsuario == usr_b.id) & (Notificacao.idRemetente == usr_a.id)) |
            ((Notificacao.idUsuario == usr_a.id) & (Notificacao.idRemetente == usr_b.id)) |
            (Notificacao.idUsuario == usr_a.id)
        ).delete()
        db.commit()

        # ----------------------------------------------------
        # TESTE 1: Seguidor (A segue B -> B recebe notificação)
        # ----------------------------------------------------
        print("\n[2/8] TESTE 1: Usuário A segue Usuário B (Notificação de FOLLOW)...")
        # Garantir limpa de relacionamento prévio
        rel_prev = SeguidorService.deixar_de_seguir(db, usr_a.id, usr_b.id) if SeguidorService.obter_status_relacionamento(db, usr_a.id, usr_b.id).seguindo else None
        
        rel_new = SeguidorService.seguir(db, usr_a.id, usr_b.id)
        notifs_b = NotificacaoService.listar_notificacoes(db, usr_b.id)
        notif_follow = next((n for n in notifs_b if n.tipo == "FOLLOW" and n.idRemetente == usr_a.id), None)
        assert notif_follow is not None, "Usuário B deve receber notificação FOLLOW"
        assert notif_follow.remetente is not None, "Objeto remetente deve estar populado"
        assert notif_follow.remetente.id == usr_a.id
        print(f"  [OK] Notificação FOLLOW recebida por B com remetente '{notif_follow.remetente.nome}' (ID {notif_follow.remetente.id})")

        # ----------------------------------------------------
        # TESTE 2: Comentário (A comenta na obra de B -> B recebe notificação)
        # ----------------------------------------------------
        print("\n[3/8] TESTE 2: Usuário A comenta na postagem de B (Notificação de COMMENT)...")
        coment_dados = ComentarioCriar(conteudo="Trabalho incrível, parabéns!")
        comentario_a = ComentarioService.criar_comentario(db, usr_a.id, post_b.id, coment_dados)

        notifs_b_post = NotificacaoService.listar_notificacoes(db, usr_b.id)
        notif_comment = next((n for n in notifs_b_post if n.tipo == "COMMENT" and n.idComentario == comentario_a.id), None)
        assert notif_comment is not None, "Usuário B deve receber notificação COMMENT"
        assert notif_comment.idPostagem == post_b.id
        assert notif_comment.idRemetente == usr_a.id
        print(f"  [OK] Notificação COMMENT recebida por B: '{notif_comment.mensagem}' (Post ID {notif_comment.idPostagem})")

        # ----------------------------------------------------
        # TESTE 3: Perfil pelo comentário (Dados do autor no comentário)
        # ----------------------------------------------------
        print("\n[4/8] TESTE 3: Verificando se os comentários expõem id, nome e fotoPerfil do autor...")
        comentarios_post_b = ComentarioService.listar_comentarios(db, post_b.id)
        assert len(comentarios_post_b) > 0
        coment_obj = comentarios_post_b[0]
        schema_coment = ComentarioResposta.model_validate(coment_obj)
        assert schema_coment.usuario is not None
        assert schema_coment.usuario.id == usr_a.id
        assert schema_coment.usuario.nome == usr_a.nome
        print(f"  [OK] Dados do autor do comentário verificados: ID {schema_coment.usuario.id} | Nome: '{schema_coment.usuario.nome}'")

        # ----------------------------------------------------
        # TESTE 4: Perfil Visitado (Dados e Obras de A)
        # ----------------------------------------------------
        print("\n[5/8] TESTE 4: Consultando perfil público e obras do Usuário A...")
        perfil_a = UsuarioService.obter_perfil_publico(db, target_id=usr_a.id, me_id=usr_b.id)
        assert perfil_a.id == usr_a.id
        assert perfil_a.nome == usr_a.nome
        assert perfil_a.obrasCount >= 1

        obras_a = PostagemService.listar_obras(db, usuario_id=usr_a.id)
        assert all(o.usuario.id == usr_a.id for o in obras_a if hasattr(o, "usuario"))
        print(f"  [OK] Perfil público de A validado com sucesso! Total de obras de A: {len(obras_a)}")

        # ----------------------------------------------------
        # TESTE 5: Não notificar o próprio usuário (A comenta na própria obra)
        # ----------------------------------------------------
        print("\n[6/8] TESTE 5: Testando auto-comentário (A comenta na obra de A)...")
        qtd_notifs_a_antes = len(NotificacaoService.listar_notificacoes(db, usr_a.id))
        coment_auto = ComentarioService.criar_comentario(db, usr_a.id, post_a.id, ComentarioCriar(conteudo="Meu próprio comentário na minha obra"))
        qtd_notifs_a_depois = len(NotificacaoService.listar_notificacoes(db, usr_a.id))
        assert qtd_notifs_a_depois == qtd_notifs_a_antes, "Usuário A NÃO pode receber notificação ao comentar na própria obra"
        print("  [OK] Auto-notificação evitada com sucesso! Nenhuma notificação criada para ação própria.")

        # ----------------------------------------------------
        # TESTE 6: Não duplicar notificações
        # ----------------------------------------------------
        print("\n[7/8] TESTE 6: Verificando não-duplicidade em ações únicas...")
        count_follow_notifs = len([n for n in NotificacaoService.listar_notificacoes(db, usr_b.id) if n.tipo == "FOLLOW" and n.idRemetente == usr_a.id])
        assert count_follow_notifs == 1, "Deve existir exatamente 1 notificação de FOLLOW para a mesma ação"
        print("  [OK] Nenhuma notificação duplicada encontrada!")

        # ----------------------------------------------------
        # TESTE 7 & 8: Leitura, Contagem e Segurança
        # ----------------------------------------------------
        print("\n[8/8] TESTES 7 e 8: Leitura, Contadores e Segurança de Notificações...")
        nao_lidas_b = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        assert nao_lidas_b >= 1, "Usuário B deve ter notificações não lidas"

        # Tentar marcar notificação de B usando o ID de A -> deve dar 403 Forbidden
        notif_b_id = notif_follow.id
        try:
            NotificacaoService.marcar_como_lida(db, usuario_id=usr_a.id, notificacao_id=notif_b_id)
            print("  [ERRO] O sistema permitiu que A alterasse notificação de B!")
            sys.exit(1)
        except HTTPException as e:
            assert e.status_code == 403
            print(f"  [OK] Segurança validada: A recebeu HTTP {e.status_code} ao tentar alterar notificação de B.")

        # Marcar notificação como lida pelo próprio proprietário (B)
        notif_lida = NotificacaoService.marcar_como_lida(db, usuario_id=usr_b.id, notificacao_id=notif_b_id)
        assert notif_lida.lida == True
        print("  [OK] Notificação marcada como lida com sucesso pelo proprietário B!")

        # Limpeza final dos objetos criados
        ComentarioService.deletar_comentario(db, usr_a.id, comentario_a.id, "cliente")
        ComentarioService.deletar_comentario(db, usr_a.id, coment_auto.id, "cliente")
        PostagemService.deletar_postagem(db, post_a.id, usr_a.id)
        PostagemService.deletar_postagem(db, post_b.id, usr_b.id)
        SeguidorService.deixar_de_seguir(db, usr_a.id, usr_b.id)

        print("\n=== TODOS OS 8 TESTES DA BATERIA DE NOTIFICAÇÕES E COMENTÁRIOS PASSARAM COM SUCESSO! ===")

    except Exception as e:
        print(f"\n[ERRO FATAL NOS TESTES]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    testar_notificacoes_e_comentarios()
