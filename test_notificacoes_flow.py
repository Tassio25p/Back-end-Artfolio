import sys
from fastapi import HTTPException
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.usuario_model import Usuario
from app.models.curtida_model import Curtida
from app.models.comentario_model import Comentario
from app.models.seguidor_model import Seguidor
from app.models.conversa_model import Conversa
from app.models.conversa_usuario_model import ConversaUsuario
from app.models.mensagem_model import Mensagem
from app.models.notificacao_model import Notificacao
from app.schemas.comentario_schema import ComentarioCriar
from app.services.curtida_service import CurtidaService
from app.services.comentario_service import ComentarioService
from app.services.seguidor_service import SeguidorService
from app.services.notificacao_service import NotificacaoService


def testar_fluxo_notificacoes():
    print("=== ARTFOLIO BACKEND: TESTE DO MÓDULO DE NOTIFICAÇÕES ===\n")

    # 1. Garantir conexao e criacao de tabelas
    print("[1/5] Verificando tabelas no PostgreSQL...")
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        print("  - Tabelas verificadas e conexão estabelecida com sucesso!\n")
    except Exception as e:
        print(f"[ERRO] Erro ao conectar com o banco de dados: {e}")
        sys.exit(1)

    try:
        # 2. Criar ou buscar dois usuários de teste (Usuário A e Usuário B)
        print("[2/5] Preparando usuários e obra de teste...")
        usr_a = db.query(Usuario).filter(Usuario.email == "user_a_notif@artfolio.com").first()
        if not usr_a:
            usr_a = Usuario(
                nome="João Silva (User A)",
                email="user_a_notif@artfolio.com",
                senha="hash_teste_senha",
                cpf="11122233344",
                tipo_conta="cliente"
            )
            db.add(usr_a)
            db.commit()
            db.refresh(usr_a)

        usr_b = db.query(Usuario).filter(Usuario.email == "user_b_notif@artfolio.com").first()
        if not usr_b:
            usr_b = Usuario(
                nome="Maria Artista (User B)",
                email="user_b_notif@artfolio.com",
                senha="hash_teste_senha",
                cpf="55566677788",
                tipo_conta="artista"
            )
            db.add(usr_b)
            db.commit()
            db.refresh(usr_b)

        cat = db.query(Categoria).filter(Categoria.deletado == False).first()
        if not cat:
            cat = Categoria(nomeCategoria="Pintura Digital")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        post = db.query(Postagem).filter(Postagem.idUsuario == usr_b.id, Postagem.deletado == False).first()
        if not post:
            post = Postagem(
                idUsuario=usr_b.id,
                idCategoria=cat.id,
                legenda="Obra da Maria para Teste de Notificação",
                arquivoUrl="https://artfolio.com.br/uploads/obra_maria.jpg"
            )
            db.add(post)
            db.commit()
            db.refresh(post)

        print(f"  - Usuário A (ID {usr_a.id}): {usr_a.nome}")
        print(f"  - Usuário B (ID {usr_b.id}): {usr_b.nome}")
        print(f"  - Obra do Usuário B (ID {post.id}): '{post.legenda}'\n")

        # 3. Testar disparo automático de notificações (Like, Comment, Follow)
        print("[3/5] Testando acionadores de notificação automática...")

        # A) Usuário A curte a obra do Usuário B
        try:
            CurtidaService.curtir(db, usr_a.id, post.id)
            print("  - [OK] Usuário A curtiu a obra do Usuário B.")
        except Exception:
            print("  - [INFO] Curtida já existia, ignorando erro.")

        # B) Usuário A comenta na obra do Usuário B
        comentario = ComentarioService.criar_comentario(
            db, usr_a.id, post.id, ComentarioCriar(conteudo="Ficou espetacular essa obra!")
        )
        print(f"  - [OK] Usuário A comentou na obra do Usuário B (Comentário ID {comentario.id}).")

        # C) Usuário A segue o Usuário B
        try:
            SeguidorService.seguir(db, usr_a.id, usr_b.id)
            print("  - [OK] Usuário A passou a seguir o Usuário B.")
        except Exception:
            print("  - [INFO] Relacionamento de seguir já existia.")

        # D) Usuário B curte a própria obra (NÃO deve gerar notificação para si mesmo)
        try:
            CurtidaService.curtir(db, usr_b.id, post.id)
        except Exception:
            pass

        # 4. Verificar notificações recebidas pelo Usuário B
        print("\n[4/5] Verificando notificações recebidas pelo Usuário B...")
        notifs_b = NotificacaoService.listar_notificacoes(db, usr_b.id)
        print(f"  - Total de notificações de B: {len(notifs_b)}")
        for n in notifs_b:
            print(f"    * ID {n.id} | Tipo: {n.tipo} | Título: '{n.titulo}' | Mensagem: '{n.mensagem}' | Lida: {n.lida}")

        nao_lidas_b = NotificacaoService.contar_nao_lidas(db, usr_b.id)
        print(f"  - Quantidade de notificações não lidas de B: {nao_lidas_b}")
        assert nao_lidas_b > 0, "Deveria haver notificações não lidas!"

        # 5. Testar marcação como lida, marcar todas e soft delete
        print("\n[5/5] Testando ações de gerenciamento de notificações...")
        if notifs_b:
            primeira_notif = notifs_b[0]

            # Testar marcação individual como lida
            NotificacaoService.marcar_como_lida(db, usr_b.id, primeira_notif.id)
            print(f"  - [OK] Notificação ID {primeira_notif.id} marcada como lida.")

            # Testar tentativa de marcar por outro usuário (deve falhar com 403)
            try:
                NotificacaoService.marcar_como_lida(db, usr_a.id, primeira_notif.id)
                print("  - [ERRO] Falha de segurança: Usuário A conseguiu alterar notificação de B!")
                sys.exit(1)
            except HTTPException as err:
                if err.status_code == 403:
                    print("  - [OK] Proteção de segurança confirmada: Usuário A recebeu 403 ao tentar alterar notificação de B.")

            # Testar marcar todas como lidas
            NotificacaoService.marcar_todas_como_lidas(db, usr_b.id)
            nao_lidas_apos = NotificacaoService.contar_nao_lidas(db, usr_b.id)
            print(f"  - [OK] Todas as notificações marcadas como lidas. Não lidas restantes: {nao_lidas_apos}")
            assert nao_lidas_apos == 0, "Todas deveriam estar lidas!"

            # Testar soft delete
            NotificacaoService.deletar_notificacao(db, usr_b.id, primeira_notif.id)
            print(f"  - [OK] Soft delete da notificação ID {primeira_notif.id} executado com sucesso.")

        print("\n=== FLUXO DE TESTES DE NOTIFICAÇÕES CONCLUÍDO COM SUCESSO! ===")

    except Exception as e:
        print(f"[ERRO] Falha no teste de notificações: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    testar_fluxo_notificacoes()
