import sys
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.usuario_model import Usuario
from app.services.postagem_service import PostagemService
from app.schemas.postagem_schema import PostagemResposta

def testar_fluxo_postagens():
    print("=== ARTFOLIO BACKEND: TESTE DO MÓDULO DE OBRAS (POSTAGENS) ===\n")
    
    # 1. Garantir conexao e criacao de tabelas
    print("[1/3] Verificando tabelas 'categoria' e 'postagem'...")
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        print("[OK] Conexão com o banco estabelecida e tabelas verificadas com sucesso!\n")
    except Exception as e:
        print(f"[ERRO] Erro ao conectar com o banco de dados: {e}")
        sys.exit(1)

    # 2. Inserir dados de teste caso o banco esteja vazio
    print("[2/3] Verificando ou inserindo dados de teste...")
    try:
        # Verificar se existe ao menos uma categoria
        cat = db.query(Categoria).filter(Categoria.deletado == False).first()
        if not cat:
            cat = Categoria(nomeCategoria="Pintura Digital")
            db.add(cat)
            db.commit()
            db.refresh(cat)
            print(f"  - Criada categoria de teste: ID {cat.id} - {cat.nomeCategoria}")

        # Verificar se existe ao menos um usuario
        usr = db.query(Usuario).filter(Usuario.deletado == False).first()
        if not usr:
            usr = Usuario(
                nome="Artista Exemplo",
                email="artista.teste@artfolio.com.br",
                senha="hash_senha_teste",
                cpf="98765432100",
                tipo_conta="artista"
            )
            db.add(usr)
            db.commit()
            db.refresh(usr)
            print(f"  - Criado usuário artista de teste: ID {usr.id} - {usr.nome}")

        # Verificar se existe ao menos uma postagem
        post = db.query(Postagem).filter(Postagem.deletado == False).first()
        if not post:
            post = Postagem(
                idUsuario=usr.id,
                idCategoria=cat.id,
                legenda="Arte digital conceitual gerada para teste.",
                arquivoUrl="https://artfolio.com.br/uploads/arte_teste_1.jpg"
            )
            db.add(post)
            db.commit()
            db.refresh(post)
            print(f"  - Criada postagem/obra de teste: ID {post.id}")

    except Exception as e:
        db.rollback()
        print(f"[AVISO] Erro ao inserir dados de teste: {e}")

    # 3. Testar a Service de Listagem e Busca por ID
    print("\n[3/3] Testando consultas GET via PostagemService...")
    try:
        # Testar listagem geral
        obras = PostagemService.listar_obras(db)
        print(f"  - Listar todas as obras: {len(obras)} obra(s) encontrada(s).")
        
        for o in obras:
            # Validar conversao para Pydantic Schema
            schema_obj = PostagemResposta.model_validate(o)
            print(f"    * ID: {schema_obj.id} | Legenda: {schema_obj.legenda}")
            if schema_obj.usuario:
                print(f"      Artista: {schema_obj.usuario.nome} ({schema_obj.usuario.email})")
            if schema_obj.categoria:
                print(f"      Categoria: {schema_obj.categoria.nomeCategoria}")

        # Testar busca por ID existente
        if obras:
            primeiro_id = obras[0].id
            obra_especifica = PostagemService.buscar_obra_por_id(db, primeiro_id)
            print(f"\n  - Busca por ID ({primeiro_id}): Encontrada com sucesso! Legenda: '{obra_especifica.legenda}'")

        print("\n=== FLUXO DE TESTES DE OBRAS CONCLUÍDO COM SUCESSO! ===")
    except Exception as e:
        print(f"[ERRO] Falha nos testes de serviço: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    testar_fluxo_postagens()
