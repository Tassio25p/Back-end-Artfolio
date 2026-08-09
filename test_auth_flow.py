import sys
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.schemas.usuario_schema import UsuarioCadastro, UsuarioLogin
from app.services.usuario_service import UsuarioService
from app.repositories.usuario_repository import UsuarioRepository
from app.models.usuario_model import Usuario

def testar_fluxo_autenticacao():
    print("=== ARTFOLIO BACKEND: INICIANDO TESTE DE FLUXO DE AUTENTICACAO ===\n")
    
    # 1. Testar conexão com o banco de dados
    print("[1/5] Verificando conexao com o PostgreSQL...")
    try:
        db = SessionLocal()
        # Executa uma query simples de teste
        db.execute(text("SELECT 1"))
        print("[OK] Conexao com o banco de dados estabelecida com sucesso!\n")
    except Exception as e:
        print(f"[ERRO] Erro de conexao com o banco: {e}")
        print("Certifique-se de que o PostgreSQL esta rodando e as credenciais no arquivo .env estao corretas.")
        sys.exit(1)

    # 2. Garantir compatibilidade do Schema (Adicionar tipo_conta se necessário)
    print("[2/5] Verificando colunas da tabela 'usuario'...")
    try:
        with engine.connect() as conn:
            # Verifica se a tabela usuario existe
            result_tab = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'usuario')"
            )).scalar()
            
            if not result_tab:
                print("[AVISO] Tabela 'usuario' nao encontrada. Criando tabelas...")
                from app.database import Base
                Base.metadata.create_all(bind=engine)
            
            # Verifica se tipo_conta existe
            result_col = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'usuario' AND column_name = 'tipo_conta')"
            )).scalar()
            
            if not result_col:
                print("[SQL] Coluna 'tipo_conta' ausente. Adicionando coluna a tabela 'usuario'...")
                conn.execute(text(
                    "ALTER TABLE usuario ADD COLUMN tipo_conta VARCHAR(20) NOT NULL DEFAULT 'cliente'"
                ))
                # Confirmar transação na conexão
                conn.commit()
                print("[OK] Coluna 'tipo_conta' adicionada com sucesso!\n")
            else:
                print("[OK] Tabela e colunas estao compativeis!\n")
    except Exception as e:
        print(f"[AVISO] Aviso ao verificar compatibilidade do banco: {e}\n")

    # Limpar dados de teste anteriores para garantir repetibilidade do teste
    email_teste = "teste_suporte@artfolio.com.br"
    cpf_teste = "12345678912" # CPF fictício com 11 dígitos
    nome_teste = "Jose da Silva"
    
    try:
        # 1. Buscar os IDs de usuários que podem chocar com o teste
        usuarios_chocando = db.execute(
            text("SELECT id FROM usuario WHERE email = :email OR cpf = :cpf OR nome = :nome"),
            {"email": email_teste, "cpf": cpf_teste, "nome": nome_teste}
        ).all()
        
        uids = [row[0] for row in usuarios_chocando]
        
        if uids:
            # 2. Deletar os logs desses usuários
            for uid in uids:
                db.execute(
                    text("DELETE FROM log WHERE idusuario = :uid OR (tabelaafetada = 'usuario' AND idregistroafetado = :uid)"),
                    {"uid": uid}
                )
            
            # 3. Desabilitar a trigger de soft delete para deletar fisicamente os usuários
            db.execute(text("ALTER TABLE usuario DISABLE TRIGGER trg_soft_delete_usuario"))
            
            # 4. Deletar os usuários fisicamente
            for uid in uids:
                db.execute(
                    text("DELETE FROM usuario WHERE id = :uid"),
                    {"uid": uid}
                )
            
            # 5. Reabilitar a trigger
            db.execute(text("ALTER TABLE usuario ENABLE TRIGGER trg_soft_delete_usuario"))
            
        db.commit()
        print("[OK] Limpeza de dados de teste anteriores realizada com sucesso!\n")
    except Exception as delete_err:
        db.rollback()
        print(f"[AVISO] Nao foi possivel limpar dados anteriores: {delete_err}\n")

    # 3. Testar Cadastro
    print("[3/5] Testando Cadastro de Usuario (POST /auth/cadastro)...")
    dados_cadastro = UsuarioCadastro(
        nome=nome_teste,
        email=email_teste,
        senha="senha_secreta_123",
        cpf=cpf_teste,
        telefone="11988887777",
        biografia="Desenvolvedor backend e entusiasta de artes digitais.",
        portfolio="https://artfolio.com.br/josedasilva",
        tipo_conta="artista"
    )
    
    try:
        novo_usuario = UsuarioService.cadastrar(db, dados_cadastro)
        print(f"[OK] Usuario cadastrado com sucesso!")
        print(f"  - ID: {novo_usuario.id}")
        print(f"  - Nome: {novo_usuario.nome}")
        print(f"  - E-mail: {novo_usuario.email}")
        print(f"  - Biografia: {novo_usuario.biografia}")
        print(f"  - Portfolio: {novo_usuario.portfolio}")
        print(f"  - Tipo de Conta: {novo_usuario.tipo_conta}")
        print(f"  - Senha Hash no Banco (Bcrypt): {novo_usuario.senha[:25]}...\n")
    except Exception as e:
        print(f"[ERRO] Erro ao cadastrar usuario: {e}\n")
        db.close()
        sys.exit(1)

    # 3.1 Testar Unicidade (Contas duplicadas)
    print("[3.1] Testando unicidade do cadastro (e-mail, CPF e Nome)...")
    # Tenta cadastrar com mesmo e-mail
    dados_dup_email = UsuarioCadastro(
        nome="Outro Nome", email=email_teste, senha="outrasenha", cpf="99999999999", tipo_conta="cliente"
    )
    try:
        UsuarioService.cadastrar(db, dados_dup_email)
        print("[ERRO] Falha: O sistema permitiu cadastrar e-mail duplicado!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Impediu e-mail duplicado. Mensagem: {e.detail}")

    # Tenta cadastrar com mesmo CPF
    dados_dup_cpf = UsuarioCadastro(
        nome="Outro Nome", email="outro@email.com", senha="outrasenha", cpf=cpf_teste, tipo_conta="cliente"
    )
    try:
        UsuarioService.cadastrar(db, dados_dup_cpf)
        print("[ERRO] Falha: O sistema permitiu cadastrar CPF duplicado!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Impediu CPF duplicado. Mensagem: {e.detail}")

    # Tenta cadastrar com mesmo Nome
    dados_dup_nome = UsuarioCadastro(
        nome=nome_teste, email="outro@email.com", senha="outrasenha", cpf="99999999999", tipo_conta="cliente"
    )
    try:
        UsuarioService.cadastrar(db, dados_dup_nome)
        print("[ERRO] Falha: O sistema permitiu cadastrar Nome duplicado!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Impediu Nome duplicado. Mensagem: {e.detail}\n")

    # 4. Testar Login
    print("[4/5] Testando Login de Usuario (POST /auth/login)...")
    dados_login = UsuarioLogin(
        email=email_teste,
        senha="senha_secreta_123"
    )
    
    try:
        resultado_login = UsuarioService.login(db, dados_login)
        print("[OK] Login efetuado com sucesso!")
        print(f"  - Token Tipo: {resultado_login['token_type']}")
        print(f"  - Token JWT (parcial): {resultado_login['access_token'][:30]}...")
        print(f"  - Usuario retornado: {resultado_login['usuario'].nome} ({resultado_login['usuario'].email})\n")
    except Exception as e:
        print(f"[ERRO] Erro ao fazer login: {e}\n")
        db.close()
        sys.exit(1)

    # 4.1 Testar Login com E-mail inexistente
    print("[4.1] Testando login de usuario inexistente...")
    dados_login_inexistente = UsuarioLogin(
        email="naoexiste@email.com",
        senha="senha_qualquer"
    )
    try:
        UsuarioService.login(db, dados_login_inexistente)
        print("[ERRO] Falha: O sistema permitiu login de usuario inexistente!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Login barrado (Usuario nao cadastrado). Status: {e.status_code}, Mensagem: {e.detail}")

    # 4.2 Testar Login com Senha Incorreta
    print("[4.2] Testando login com senha incorreta...")
    dados_login_incorreto = UsuarioLogin(
        email=email_teste,
        senha="senha_errada_aqui"
    )
    try:
        UsuarioService.login(db, dados_login_incorreto)
        print("[ERRO] Falha: O sistema permitiu login com senha incorreta!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Login barrado (Senha incorreta). Status: {e.status_code}, Mensagem: {e.detail}\n")

    # 5. Testar Soft Delete e seus impactos no Registro e Login
    print("[5/5] Testando fluxos de Soft Delete...")
    
    # 5.1 Realizar Soft Delete do usuário de teste (usando o DELETE padrão para acionar a trigger)
    print("  - Realizando Soft Delete do usuario cadastrado...")
    try:
        db.execute(
            text("DELETE FROM usuario WHERE email = :email"),
            {"email": email_teste}
        )
        db.commit()
        print("  - [OK] Comando DELETE executado no banco.")
    except Exception as e:
        print(f"[ERRO] Falha ao executar soft-delete: {e}")
        sys.exit(1)
        
    # Validar se o usuário continua no banco com deletado = True
    usuario_deletado_db = db.query(Usuario).filter(Usuario.email == email_teste).first()
    if usuario_deletado_db and usuario_deletado_db.deletado:
        print(f"  - [OK] Confirmado no banco: usuario ID {usuario_deletado_db.id} esta com deletado=True.")
    else:
        print("[ERRO] Falha: O usuario nao foi marcado como deletado ou foi removido fisicamente!")
        sys.exit(1)
        
    # 5.2 Tentar registrar o mesmo usuário (deve falhar por estar deletado por soft delete)
    print("  - Tentando registrar nova conta com dados de usuario deletado...")
    try:
        UsuarioService.cadastrar(db, dados_cadastro)
        print("[ERRO] Falha: O sistema permitiu recriar conta de usuario deletado!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Cadastro bloqueado. Mensagem: {e.detail}")
        
    # 5.3 Tentar logar com a conta deletada (deve falhar com 403 Forbidden)
    print("  - Tentando fazer login com a conta desativada (deletada)...")
    try:
        UsuarioService.login(db, dados_login)
        print("[ERRO] Falha: O sistema permitiu login de usuario deletado!")
        sys.exit(1)
    except Exception as e:
        print(f"  - [OK] Login bloqueado. Status: {e.status_code}, Mensagem: {e.detail}\n")

    print("=== FLUXO DE TESTE CONCLUIDO COM SUCESSO! ===")
    print("Todas as camadas (Models, Schemas, Repositories, Services, Config) estao se comunicando perfeitamente.")
    db.close()

if __name__ == "__main__":
    testar_fluxo_autenticacao()
