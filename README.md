<p align="center">
  <h1 align="center">🎨 Artfolio — Back-End API</h1>
  <p align="center">
    API RESTful completa para a plataforma de portfólio e rede social de artistas <strong>Artfolio</strong>.<br/>
    Construída com FastAPI, PostgreSQL, Redis, autenticação JWT e suporte a WebSockets/Notificações em tempo real.
  </p>
</p>

---

## 📋 Índice

- [Stack Tecnológica](#-stack-tecnológica)
- [Arquitetura do Projeto](#-arquitetura-do-projeto)
- [Configuração e Instalação](#-configuração-e-instalação)
- [Modelos de Dados (PostgreSQL)](#-modelos-de-dados-postgresql)
- [Endpoints da API](#-endpoints-da-api)
- [Segurança e Sessões](#-segurança-e-sessões)
- [Cache Redis](#-cache-redis)
- [Suíte de Testes Automatizados](#-suíte-de-testes-automatizados)

---

## 🛠 Stack Tecnológica

| Tecnologia | Versão | Papel no Sistema |
|---|---|---|
| **Python** | 3.10+ | Linguagem base da aplicação |
| **FastAPI** | 0.110+ | Framework web assíncrono e documentação Swagger |
| **SQLAlchemy** | 2.0+ | ORM para mapeamento e manipulação do PostgreSQL |
| **PostgreSQL** | 14+ | Banco de dados relacional primário |
| **Redis** | 5.0+ | Cache em memória com mecanismo de fallback gracioso |
| **Pydantic** | 2.x | Validação estrita de tipos e serialização JSON |
| **bcrypt** | — | Hashing seguro de senhas |
| **python-jose / PyJWT** | 2.x | Gerenciamento e verificação de tokens JWT |
| **httpx** | — | Integração HTTP com n8n webhook do assistente de IA |
| **Uvicorn** | 0.28+ | Servidor ASGI para desenvolvimento e produção |

---

## 🏗 Arquitetura do Projeto

O backend adota o padrão **Controller-Service-Repository-Model**, garantindo modularidade, facilidade de manutenção e desacoplamento de responsabilidades:

```text
BackEnd_Ant/
├── .env                              # Variáveis de ambiente e segredos
├── requirements.txt                  # Dependências do projeto
├── test_auth_flow.py                 # Testes de cadastro e autenticação JWT
├── test_postagens_flow.py            # Testes do fluxo de postagens e mídia
├── test_notificacoes_e_comentarios.py# Testes de comentários e notificações
├── test_realtime_notifications.py   # Testes de notificações em tempo real
├── test_salvar_e_denunciar.py        # Testes de salvar obra e denunciar obra
└── app/
    ├── main.py                       # Ponto de entrada da aplicação FastAPI
    ├── database.py                   # Conexão SQLAlchemy e SessionLocal
    ├── redis_client.py               # Cliente Redis resiliente com fallback
    ├── core/
    │   ├── config.py                 # Leitura e parsing do arquivo .env
    │   └── security.py               # Hashing bcrypt e tokens JWT
    ├── models/                       # Entidades SQLAlchemy (Mapeamento ORM)
    │   ├── usuario_model.py
    │   ├── postagem_model.py
    │   ├── categoria_model.py
    │   ├── curtida_model.py
    │   ├── comentario_model.py
    │   ├── seguidor_model.py
    │   ├── notificacao_model.py
    │   ├── obra_salva_model.py
    │   ├── denuncia_model.py
    │   ├── conversa_model.py
    │   ├── mensagem_model.py
    │   ├── assistente_conversa_model.py
    │   └── assistente_mensagem_model.py
    ├── schemas/                      # Validadores Pydantic (Request/Response)
    │   ├── usuario_schema.py
    │   ├── postagem_schema.py
    │   ├── curtida_schema.py
    │   ├── comentario_schema.py
    │   ├── seguidor_schema.py
    │   ├── notificacao_schema.py
    │   ├── obra_salva_schema.py
    │   ├── denuncia_schema.py
    │   └── assistente_schema.py
    ├── repositories/                 # Camada de Acesso a Dados (SQL/Queries)
    │   ├── usuario_repository.py
    │   ├── postagem_repository.py
    │   ├── curtida_repository.py
    │   ├── comentario_repository.py
    │   ├── seguidor_repository.py
    │   ├── notificacao_repository.py
    │   ├── obra_salva_repository.py
    │   └── denuncia_repository.py
    ├── services/                     # Regras de Negócio e Validações
    │   ├── usuario_service.py
    │   ├── postagem_service.py
    │   ├── feed_service.py
    │   ├── curtida_service.py
    │   ├── comentario_service.py
    │   ├── seguidor_service.py
    │   ├── notificacao_service.py
    │   ├── obra_salva_service.py
    │   ├── denuncia_service.py
    │   └── assistente_service.py
    └── controllers/                  # Rotas e Endpoints HTTP (FastAPI APIRouter)
        ├── auth_controller.py
        ├── usuario_controller.py
        ├── postagem_controller.py
        ├── feed_controller.py
        ├── artista_controller.py
        ├── notificacao_controller.py
        ├── admin_controller.py
        └── assistente_controller.py
```

---

## ⚙ Configuração e Instalação

### 1. Pré-requisitos
- **Python 3.10+** instalado
- Instância do **PostgreSQL** em execução
- Instância do **Redis** (opcional — o sistema possui fallback automático caso o Redis não esteja disponível)

### 2. Passo a Passo

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd BackEnd_Ant

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar as variáveis de ambiente (.env)
# Crie ou edite o arquivo .env na raiz do projeto:
```

```env
# Servidor
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True

# Banco de Dados PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_NAME=artfolio_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Autenticação JWT
JWT_SECRET_KEY=sua_chave_secreta_super_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Uploads
UPLOAD_DIR=uploads
```

```bash
# 5. Executar o servidor de desenvolvimento
python -m app.main
```

A API estará rodando em `http://localhost:8000`.  
A documentação Swagger interativa pode ser acessada em `http://localhost:8000/docs`.

---

## 🗄 Modelos de Dados (PostgreSQL)

O sistema possui **13 entidades ativas** no banco de dados:

1. **`Usuario`** (`usuario`): Cadastro de usuários (artistas, clientes, moderadores, admins), fotos de perfil, biografias, portfólios.
2. **`Postagem`** (`postagem`): Obras publicadas pelos artistas, com suporte a legenda, categoria e URL do arquivo.
3. **`Categoria`** (`categoria`): Categorias de arte (Ex: Pintura Digital, 3D Art, Têxtil, Ilustração).
4. **`Curtida`** (`curtida`): Likes registrados nas postagens (`idusuario`, `idpostagem`).
5. **`Comentario`** (`comentario`): Comentários em postagens com suporte a soft delete.
6. **`Seguidor`** (`seguidor`): Relacionamentos de seguidores/seguindo entre usuários (`idseguidor`, `idseguido`).
7. **`Notificacao`** (`notificacao`): Notificações de novos seguidores, curtidas e comentários, com status lido/não lido.
8. **`ObraSalva`** (`obra_salva`): Coleção de obras salvas por cada usuário com restrição de unicidade `UNIQUE(idusuario, idpostagem)`.
9. **`Denuncia`** (`denuncia`): Denúncias enviadas pelos usuários sobre obras/conteúdos, com status de moderação (`PENDENTE`, `EM_ANALISE`, `RESOLVIDA`, `REJEITADA`).
10. **`Conversa`** & **`Mensagem`**: Estrutura para chat privado entre usuários da plataforma.
11. **`AssistenteConversa`** & **`AssistenteMensagem`**: Histórico de diálogos com o assistente inteligente de IA.

---

## 🌐 Endpoints da API

### 🔐 Autenticação (`/auth`)
- `POST /auth/cadastro` — Cadastrar nova conta com validação de e-mail e CPF únicos.
- `POST /auth/login` — Autenticar e obter Token JWT + dados do usuário.
- `GET /auth/me` — Obter dados da conta atualmente autenticada.

### 👤 Usuários e Perfis (`/usuarios`)
- `PUT /usuarios/me` — Atualizar perfil do usuário autenticado.
- `POST /usuarios/me/foto-perfil` — Upload de foto de perfil.
- `POST /usuarios/{id}/seguir` — Seguir um usuário.
- `DELETE /usuarios/{id}/seguir` — Deixar de seguir um usuário.
- `GET /usuarios/{id}/seguidores` — Listar seguidores de um usuário.
- `GET /usuarios/{id}/seguindo` — Listar quem o usuário segue.
- `GET /usuarios/{id}/status-relacionamento` — Checar estado atual de relacionamento entre usuários.

### 🖼 Obras e Feed (`/postagens`, `/feed`, `/obras`)
- `GET /feed` — Retorna o feed cronológico enriquecido com contadores (`likes`, `comentarios`, `seguidores`) e flags (`curtido_por_mim`, `seguindo_usuario`, `salvo_por_mim`).
- `GET /obras` / `GET /postagens/{id}` — Listar e buscar detalhes de postagens.
- `POST /postagens` — Criar nova postagem/obra.
- `PUT /postagens/{id}` — Editar postagem.
- `DELETE /postagens/{id}` — Excluir postagem (soft delete).
- `POST /postagens/{id}/like` / `DELETE /postagens/{id}/like` — Curtir / Descurtir obra.
- `POST /postagens/{id}/comentarios` / `GET /postagens/{id}/comentarios` — Adicionar e listar comentários.

### 🔖 Obras Salvas (`/postagens/.../salvar`)
- `POST /postagens/{id}/salvar` — Salvar obra na coleção pessoal.
- `DELETE /postagens/{id}/salvar` — Remover obra dos salvos.
- `GET /postagens/salvas` — Listar todas as obras salvas pelo usuário autenticado.
- `GET /postagens/{id}/salvo` — Retorna se a obra específica está salva.

### 🚩 Denúncias & Moderação (`/postagens/.../denunciar`, `/admin`)
- `POST /postagens/{id}/denunciar` — Enviar denúncia (valida motivo obrigatório e impede auto-denúncia ou denúncias duplicadas).
- `GET /admin/denuncias` — Central de denúncias para moderadores e administradores.
- `PATCH /admin/denuncias/{id}` — Atualizar status de moderação (`RESOLVIDA`, `REJEITADA`, `EM_ANALISE`).

### 🔔 Notificações (`/notificacoes`)
- `GET /notificacoes` — Listar notificações do usuário.
- `GET /notificacoes/nao-lidas/count` — Contador em tempo real de notificações não lidas.
- `PATCH /notificacoes/{id}/ler` — Marcar notificação específica como lida.
- `PATCH /notificacoes/marcar-todas-lidas` — Marcar todas as notificações como lidas.

### 🤖 Assistente de IA (`/assistente`)
- `POST /assistente/mensagem` — Enviar mensagem ao chatbot integrado ao n8n.
- `GET /assistente/conversas` — Listar histórico de conversas ativas.

---

## 🧪 Suíte de Testes Automatizados

A aplicação conta com scripts dedicados para validação de cada módulo principal:

```bash
# Teste de Autenticação e JWT
python test_auth_flow.py

# Teste de Postagens e Feed
python test_postagens_flow.py

# Teste de Notificações e Comentários
python test_notificacoes_e_comentarios.py

# Teste de Notificações em Tempo Real (Polling & Contadores)
python test_realtime_notifications.py

# Teste de Salvar Obra e Denúncias (Persistência, Unicidade & Moderação)
python test_salvar_e_denunciar.py
```

---

<p align="center">
  <sub>Artfolio © 2026 — Trabalho de Conclusão de Curso</sub>
</p>
