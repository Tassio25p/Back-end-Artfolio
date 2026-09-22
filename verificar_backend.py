import os
import sys
import importlib
import inspect
import traceback
from datetime import datetime

# Garante o diretório raiz no PATH
sys.path.insert(0, os.path.abspath("."))

ERROS_ENCONTRADOS = []
ALERTAS_ENCONTRADOS = []

def registrar_erro(origem: str, detalhe: str):
    ERROS_ENCONTRADOS.append((origem, detalhe))

def registrar_alerta(origem: str, detalhe: str):
    ALERTAS_ENCONTRADOS.append((origem, detalhe))

print("=" * 70)
print("1. TESTE DE IMPORTAÇÃO DINÂMICA DE TODOS OS FICHEIROS .PY")
print("=" * 70)

for root, _, files in os.walk("app"):
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            caminho_completo = os.path.join(root, file)
            caminho_modulo = caminho_completo.replace(os.path.sep, ".").replace(".py", "")
            try:
                importlib.import_module(caminho_modulo)
                print(f"  [OK] {caminho_modulo}")
            except Exception as e:
                print(f"  [FALHA] {caminho_modulo}: {e}")
                registrar_erro(caminho_modulo, f"Erro de Importação/Sintaxe: {e}")

print("\n" + "=" * 70)
print("2. VERIFICAÇÃO DE MODELOS E ATRIBUTOS CRÍTICOS (SQLALCHEMY)")
print("=" * 70)

try:
    from app.models.usuario_model import Usuario
    from app.models.categoria_model import Categoria
    from app.models.postagem_model import Postagem

    # 1. Checagem do Usuario
    colunas_usuario = [c.name for c in Usuario.__table__.columns]
    if "tipo_conta" not in colunas_usuario:
        registrar_erro("UsuarioModel", "Coluna 'tipo_conta' ausente na tabela usuario.")
    if not hasattr(Usuario, "plano") and "plano" not in colunas_usuario:
        registrar_alerta("UsuarioModel", "Modelo Usuario não tem propriedade ou coluna 'plano' (usa-se 'tipo_conta').")

    # 2. Checagem da Categoria
    colunas_categoria = [c.name for c in Categoria.__table__.columns]
    if "nomeCategoria" not in colunas_categoria and "nome" in colunas_categoria:
        registrar_alerta("CategoriaModel", "Coluna chama-se 'nome' em vez de 'nomeCategoria'.")
    elif "nomeCategoria" in colunas_categoria and not hasattr(Categoria, "nome"):
        print("  [OK] Categoria utiliza 'nomeCategoria' como esperado.")

    # 3. Checagem da Postagem
    colunas_postagem = [c.name for c in Postagem.__table__.columns]
    for col in ["preco", "a_venda", "permite_download"]:
        if col not in colunas_postagem:
            registrar_alerta("PostagemModel", f"Coluna da Fase 4 '{col}' ainda não mapeada no modelo.")

except Exception as e:
    registrar_erro("ValidacaoModelos", f"Falha ao validar modelos SQLAlchemy: {e}")

print("\n" + "=" * 70)
print("3. VERIFICAÇÃO DE CONEXÃO COM POSTGRESQL E TABELAS")
print("=" * 70)

try:
    from app.database import SessionLocal, engine
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("  [OK] Conexão com a base de dados ativa e funcional.")
except Exception as e:
    registrar_erro("Database", f"Incapaz de conectar ao PostgreSQL: {e}")

print("\n" + "=" * 70)
print("4. BUSCA POR FUNÇÕES DEPRECIADAS (DATETIME.UTCNOW)")
print("=" * 70)

total_utcnow = 0
for root, _, files in os.walk("app"):
    for file in files:
        if file.endswith(".py"):
            caminho = os.path.join(root, file)
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                linhas = f.readlines()
                for i, linha in enumerate(linhas, 1):
                    if "datetime.utcnow" in linha or ".utcnow()" in linha:
                        total_utcnow += 1
                        registrar_alerta(f"{caminho}:{i}", "Uso de datetime.utcnow() deprecado.")

print(f"  Ocorrências encontradas: {total_utcnow}")

print("\n" + "=" * 70)
print("RELATÓRIO FINAL DO DIAGNÓSTICO")
print("=" * 70)

print(f"Total de Erros Críticos (Impedem arranque): {len(ERROS_ENCONTRADOS)}")
for origem, detalhe in ERROS_ENCONTRADOS:
    print(f"  [X] {origem} -> {detalhe}")

print(f"\nTotal de Alertas e Inconsistências: {len(ALERTAS_ENCONTRADOS)}")
for origem, detalhe in ALERTAS_ENCONTRADOS:
    print(f"  [!] {origem} -> {detalhe}")

if ERROS_ENCONTRADOS:
    sys.exit(1)