import sys
import time
import json
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models.categoria_model import Categoria
from app.models.postagem_model import Postagem
from app.models.usuario_model import Usuario
from app.services.postagem_service import PostagemService
from app.services.usuario_service import UsuarioService
from app.redis_client import redis_client

def testar_integracao_redis():
    print("=== ARTFOLIO BACKEND: TESTE DE INTEGRAÇÃO DO REDIS ===\n")

    # 1. Testar conexão com Redis (redis-artfolio na porta 6380)
    print("[1/5] Testando conexão com o container 'redis-artfolio'...")
    if redis_client.client:
        try:
            ping_res = redis_client.client.ping()
            print(f"  [OK] Conectado ao Redis na porta 6380! Resposta PING: {ping_res}")
        except Exception as e:
            print(f"  [ERRO] Falha ao enviar PING ao Redis: {e}")
            sys.exit(1)
    else:
        print("  [ERRO] redis_client não está conectado ao Redis.")
        sys.exit(1)

    # 2. Inicializar banco e garantir dados de teste
    print("\n[2/5] Inicializando sessão no PostgreSQL...")
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        cat = db.query(Categoria).first()
        if not cat:
            cat = Categoria(nomeCategoria="Arte Digital Redis Test")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        usr = db.query(Usuario).first()
        if not usr:
            usr = Usuario(
                nome="Usuario Redis Test",
                email="redis.test@artfolio.com.br",
                senha="hash_teste_redis",
                cpf="11122233344",
                tipo_conta="artista"
            )
            db.add(usr)
            db.commit()
            db.refresh(usr)
        print("  [OK] Sessão no banco de dados pronta.")
    except Exception as e:
        print(f"  [ERRO] Falha ao preparar banco de dados: {e}")
        db.close()
        sys.exit(1)

    # 3. Teste de Cache (MISS depois HIT)
    print("\n[3/5] Testando ciclo de Cache de Obras (MISS e HIT)...")
    cache_key_obras = "artfolio:obras:user_all_cat_all"
    
    # Limpa chave antes do teste
    redis_client.delete_pattern("artfolio:obras:*")
    print(f"  - Limpando cache '{cache_key_obras}' antes do teste.")
    assert redis_client.get(cache_key_obras) is None, "Chave deveria estar vazia antes da consulta"

    # Primeira chamada: MISS
    t0 = time.time()
    obras_1 = PostagemService.listar_obras(db)
    t_miss = (time.time() - t0) * 1000
    print(f"  - 1ª Chamada (MISS - busca no PostgreSQL): {t_miss:.2f}ms | {len(obras_1)} obras retornadas.")
    
    # Verificar se o Redis foi populado
    val_no_redis = redis_client.get(cache_key_obras)
    assert val_no_redis is not None, "Redis deveria ter sido populado com o cache de obras"
    print("  [OK] Cache salvo com sucesso no Redis!")

    # Segunda chamada: HIT
    t1 = time.time()
    obras_2 = PostagemService.listar_obras(db)
    t_hit = (time.time() - t1) * 1000
    print(f"  - 2ª Chamada (HIT - busca direta no Redis): {t_hit:.2f}ms | {len(obras_2)} obras retornadas.")
    assert len(obras_1) == len(obras_2), "Quantidade de obras no HIT deve bater com a do MISS"
    print("  [OK] Teste HIT / MISS concluído com sucesso!")

    # 4. Teste de Invalidação de Cache
    print("\n[4/5] Testando Invalidação de Cache no evento POST/PUT/DELETE...")
    from app.schemas.postagem_schema import PostagemCriar
    dados_nova_postagem = PostagemCriar(
        idCategoria=cat.id,
        legenda="Obra de teste para invalidação do cache",
        arquivoUrl="https://artfolio.com.br/uploads/teste_invalida.jpg"
    )
    postagem_criada = PostagemService.criar_postagem(db, usr.id, dados_nova_postagem)
    print(f"  - Nova postagem criada (ID {postagem_criada.id}). Invalidação disparada.")
    
    # Verificar se a chave foi invalidada
    val_apos_invalida = redis_client.get(cache_key_obras)
    assert val_apos_invalida is None, "O cache artfolio:obras:* deveria ter sido apagado após criar postagem"
    print("  [OK] Invalidação do cache Redis verificada com sucesso!")

    # Limpeza da postagem criada
    PostagemService.deletar_postagem(db, postagem_criada.id, usr.id)

    # 5. Teste de Resiliência (Fallback quando Redis desconectado)
    print("\n[5/5] Testando Resiliência e Fallback para PostgreSQL (simulando Redis Offline)...")
    client_original = redis_client.client
    redis_client.client = None  # Simula Redis offline

    try:
        obras_offline = PostagemService.listar_obras(db)
        print(f"  - Consulta com Redis offline: {len(obras_offline)} obras retornadas do PostgreSQL via Fallback.")
        print("  [OK] O sistema continuou funcionando perfeitamente sem exceções!")
    except Exception as e:
        print(f"  [ERRO] O sistema falhou quando o Redis estava offline: {e}")
        sys.exit(1)
    finally:
        redis_client.client = client_original  # Restaura conexão
        db.close()

    print("\n=== TODOS OS TESTES DE INTEGRAÇÃO DO REDIS FORAM CONCLUÍDOS COM SUCESSO! ===")

if __name__ == "__main__":
    testar_integracao_redis()
