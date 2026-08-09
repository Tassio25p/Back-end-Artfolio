<p align="center">
  <h1 align="center">🎨 Artfolio — Back-End API</h1>
  <p align="center">
    API RESTful para a plataforma artística digital <strong>Artfolio</strong>.<br/>
    Construída com FastAPI, PostgreSQL, Redis e autenticação JWT.
  </p>
</p>

---

## 📋 Índice

- [Stack Tecnológica](#-stack-tecnológica)
- [Arquitetura](#-arquitetura)
- [Configuração e Instalação](#-configuração-e-instalação)
- [Modelos de Dados](#-modelos-de-dados)
- [Endpoints da API](#-endpoints-da-api)
- [Segurança](#-segurança)
- [Cache Redis](#-cache-redis)
- [Testes](#-testes)
- [Status do Desenvolvimento](#-status-do-desenvolvimento)

---

## 🛠 Stack Tecnológica

| Tecnologia | Versão | Papel |
|---|---|---|
| **Python** | 3.10+ | Linguagem principal |
| **FastAPI** | 0.110–0.111 | Framework web (REST API) |
| **SQLAlchemy** | 2.x | ORM para acesso ao banco de dados |
| **PostgreSQL** | — | Banco de dados relacional |
| **Redis** | 5.x | Cache com fallback seguro |
| **Pydantic** | 2.x | Validação e serialização de dados |
| **bcrypt** | — | Hashing de senhas |
| **python-jose** | 3.x | Tokens JWT para autenticação |
| **httpx** | — | Comunicação assíncrona com n8n |
| **Uvicorn** | 0.28–0.30 | Servidor ASGI |

---

## 🏗 Arquitetura

O projeto segue uma **arquitetura em camadas** com separação clara de responsabilidades:

```
BackEnd_Ant/
├── .env                        # Variáveis de ambiente
├── requirements.txt            # Dependências Python
├── uploads/                    # Diretório para arquivos enviados
├── test_auth_flow.py           # Testes do fluxo de autenticação
├── test_postagens_flow.py      # Testes do fluxo de postagens
└── app/
    ├── main.py                 # Ponto de entrada da aplicação
    ├── database.py             # Configuração do SQLAlchemy + PostgreSQL
    ├── redis_client.py         # Cliente Redis com fallback seguro
    ├── core/
    │   ├── config.py           # Configurações globais (leitura do .env)
    │   └── security.py         # Hashing de senhas e geração de JWT
    ├── models/                 # Modelos SQLAlchemy (mapeamento das tabelas)
    │   ├── usuario_model.py
    │   ├── artista_model.py
    │   ├── postagem_model.py
    │   ├── categoria_model.py
    │   ├── conversa_model.py
    │   ├── conversa_usuario_model.py
    │   ├── mensagem_model.py
    │   ├── plano_model.py
    │   ├── assinatura_model.py
    │   ├── assistente_conversa_model.py
    │   ├── assistente_mensagem_model.py
    │   └── log_model.py
    ├── schemas/                # Schemas Pydantic (validação de entrada/saída)
    │   ├── usuario_schema.py
    │   ├── artista_schema.py
    │   ├── postagem_schema.py
    │   └── assistente_schema.py
    ├── repositories/           # Camada de acesso a dados (queries)
    │   ├── usuario_repository.py
    │   ├── artista_repository.py
    │   ├── postagem_repository.py
    │   └── assistente_repository.py
    ├── services/               # Regras de negócio
    │   ├── usuario_service.py
    │   ├── artista_service.py
    │   ├── postagem_service.py
    │   └── assistente_service.py
    └── controllers/            # Definição das rotas HTTP
        ├── auth_controller.py
        ├── artista_controller.py
        ├── postagem_controller.py
        └── assistente_controller.py
```

### Fluxo de uma Requisição

```
Cliente HTTP → Controller (rota) → Service (regra de negócio) → Repository (query) → Model (ORM) → PostgreSQL
```

| Camada | Responsabilidade |
|---|---|
| **Controllers** | Definem as rotas HTTP, recebem requisições e retornam respostas |
| **Services** | Aplicam regras de negócio, validações e orquestração |
| **Repositories** | Executam queries no banco via SQLAlchemy |
| **Models** | Mapeiam tabelas do PostgreSQL como classes Python |
| **Schemas** | Validam dados de entrada e formatam dados de saída |
| **Core** | Configuração global (.env) e segurança (JWT, bcrypt) |

---

## ⚙ Configuração e Instalação

### Pré-requisitos

- Python 3.10+
- PostgreSQL instalado e rodando
- Redis instalado (opcional — o sistema funciona sem ele)

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd BackEnd_Ant
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Edite o arquivo `.env` na raiz do projeto:

```env
# Configurações do Servidor
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True

# Configurações do PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=123456
DB_NAME=dbver

# Configurações do Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Configurações de Segurança e JWT
JWT_SECRET_KEY=9476cf647ea376a9172f3a9e3381a179ceb6cf6a27e7f1e63a129d2f23ea6e61
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Diretórios
UPLOAD_DIR=uploads
```

### 5. Iniciar o servidor

```bash
python -m app.main
```

O servidor estará disponível em `http://localhost:8000`.  
A documentação interativa (Swagger UI) estará em `http://localhost:8000/docs`.

---

## 🗄 Modelos de Dados

O sistema possui **12 modelos** mapeados para tabelas PostgreSQL. Todos os modelos que suportam deleção utilizam **soft delete** (campo `deletado` + `dataDelecao`).

### Usuários e Autenticação

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `Usuario` | `usuario` | id, nome, email, senha (hash), cpf, telefone, biografia, fotoPerfil, portfolio, tipo_conta, dataCriacao, deletado |
| `Artista` | — | Alias de `Usuario` com filtro `tipo_conta = 'artista'` |

> **Tipos de conta válidos:** `cliente`, `artista`, `moderador`, `admin`

### Obras (Postagens)

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `Postagem` | `postagem` | id, idUsuario (FK), idCategoria (FK), legenda, arquivoUrl, dataPostagem, deletado |
| `Categoria` | `categoria` | id, nomeCategoria, deletado |

### Chat entre Usuários

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `Conversa` | `conversa` | id, dataCriacao, deletado |
| `ConversaUsuario` | `conversausuario` | idConversa (PK/FK), idUsuario (PK/FK), dataEntrada, deletado |
| `Mensagem` | `mensagem` | id, idRemetente (FK), idConversa (FK), conteudo, arquivoUrl, dataEnvio, deletado |

### Planos e Assinaturas

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `Plano` | `plano` | id, isAtivo, tipo, descricao, deletado |
| `Assinatura` | `assinatura` | id, idUsuario (FK), idPlano (FK), dataInicio, dataFim, ativa, deletado |

### Assistente de IA (Chatbot)

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `AssistenteConversa` | `assistente_conversa` | id, idUsuario (FK), titulo, dataInicio, dataAtualizacao, ativa, deletado |
| `AssistenteMensagem` | `assistente_mensagem` | id, idConversa (FK), remetente, mensagem, ferramentaUsada, respostaJson (JSONB), dataEnvio, deletado |

### Auditoria

| Modelo | Tabela | Campos Principais |
|---|---|---|
| `Log` | `log` | id, idUsuario (FK), acao, tabelaAfetada, dataHora, idRegistroAfetado, descricao |

### Diagrama ER

```
USUARIO ──┬──< POSTAGEM >──── CATEGORIA
          ├──< ASSINATURA >── PLANO
          ├──< CONVERSAUSUARIO >── CONVERSA ──< MENSAGEM
          ├──< ASSISTENTE_CONVERSA ──< ASSISTENTE_MENSAGEM
          └──< LOG
```

---

## 🌐 Endpoints da API

### 🔐 Autenticação (`/auth`)

| Método | Rota | Descrição | Autenticação |
|---|---|---|---|
| `POST` | `/auth/cadastro` | Cadastra novo usuário | ❌ Pública |
| `POST` | `/auth/login` | Realiza login e retorna JWT | ❌ Pública |
| `GET` | `/auth/me` | Retorna dados do usuário logado | ✅ JWT |

**Validações do cadastro:**
- E-mail único (bloqueia inclusive contas deletadas)
- CPF único (bloqueia inclusive contas deletadas)
- Nome de usuário único (bloqueia inclusive contas deletadas)
- Senha mínima de 6 caracteres
- Tipo de conta válido (cliente, artista, moderador, admin)

**Retorno do login:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "nome": "João Silva",
    "email": "joao@email.com",
    "tipo_conta": "artista",
    ...
  }
}
```

---

### 🖼 Obras / Postagens (`/obras` ou `/postagens`)

| Método | Rota | Descrição | Autenticação |
|---|---|---|---|
| `GET` | `/obras` | Lista todas as obras ativas | ❌ Pública |
| `GET` | `/obras/{id}` | Busca obra por ID | ❌ Pública |
| `POST` | `/postagens` | Cria nova obra | ❌ Pública |
| `PUT` | `/postagens/{id}` | Atualiza obra existente | ❌ Pública |
| `DELETE` | `/postagens/{id}` | Remove obra (soft delete) | ❌ Pública |

**Query params para listagem:**
- `usuario_id` — Filtra obras de um artista específico
- `categoria_id` — Filtra obras de uma categoria específica

**Resposta inclui dados aninhados:**
```json
{
  "id": 1,
  "legenda": "Arte conceitual cyberpunk",
  "arquivoUrl": "https://...",
  "usuario": { "id": 5, "nome": "Ana Costa", "tipo_conta": "artista" },
  "categoria": { "id": 2, "nomeCategoria": "Pintura Digital" }
}
```

---

### 🎨 Artistas (`/artistas`)

| Método | Rota | Descrição | Autenticação |
|---|---|---|---|
| `GET` | `/artistas` | Lista todos os artistas ativos | ❌ Pública |
| `GET` | `/artistas/busca?nome=...` | Busca artistas por nome (parcial, case-insensitive) | ❌ Pública |
| `GET` | `/artistas/{id}` | Busca artista por ID | ❌ Pública |

---

### 🤖 Assistente de IA (`/assistente`)

| Método | Rota | Descrição | Autenticação |
|---|---|---|---|
| `POST` | `/assistente/mensagem` | Envia mensagem ao chatbot IA | ✅ JWT |
| `GET` | `/assistente/conversas` | Lista conversas do usuário | ✅ JWT |
| `GET` | `/assistente/conversas/{id}` | Busca conversa com histórico completo | ✅ JWT |
| `PATCH` | `/assistente/conversas/{id}/encerrar` | Encerra (marca como inativa) uma conversa | ✅ JWT |
| `DELETE` | `/assistente/conversas/{id}` | Soft delete da conversa | ✅ JWT |

**Funcionamento:**
1. Usuário envia mensagem (pode informar `idConversa` existente ou criar nova)
2. Mensagem do usuário é salva no banco
3. Texto é enviado ao webhook do **n8n** (`http://localhost:5678/webhook/artfolio-agent`)
4. Resposta da IA é salva no banco (texto + JSON bruto)
5. Retorna ambas as mensagens + ID da conversa

**Segurança:** O usuário só pode acessar **suas próprias conversas**.

---

### ❤️ Healthcheck

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Verifica se a API está online |

```json
{
  "status": "Online",
  "projeto": "Artfolio API",
  "documentacao": "/docs"
}
```

---

## 🔒 Segurança

### Autenticação JWT

- **Algoritmo:** HS256
- **Expiração:** 24 horas (1440 minutos)
- **Payload do token:** `sub` (ID do usuário), `email`, `tipo_conta`, `exp`
- **Proteção de rotas:** Dependency `obter_usuario_atual` valida o token Bearer em cada requisição protegida

### Hashing de Senhas

- **Algoritmo:** bcrypt com salt aleatório
- Senhas **nunca** são retornadas nas respostas da API
- Comparação segura contra timing attacks

---

## 📦 Cache Redis

O sistema utiliza um cliente Redis com **fallback seguro** (`SafeRedisClient`):

- Se o Redis estiver **online**: cache funciona normalmente (get, set com TTL, delete)
- Se o Redis estiver **offline**: todos os métodos retornam `None`/`False` silenciosamente e a aplicação continua funcionando diretamente com o PostgreSQL
- Timeout de conexão curto (2 segundos) para evitar gargalos

---

## 🧪 Testes

### Teste de Autenticação

```bash
python -m test_auth_flow
```

Testa o fluxo completo:
1. Conexão com o PostgreSQL
2. Compatibilidade do schema (coluna `tipo_conta`)
3. Cadastro de usuário
4. Unicidade (e-mail, CPF, nome duplicados)
5. Login com credenciais válidas
6. Login com e-mail inexistente
7. Login com senha incorreta
8. Soft delete e impactos no cadastro/login

### Teste de Postagens

```bash
python -m test_postagens_flow
```

Testa o fluxo de obras:
1. Criação de tabelas
2. Inserção de dados de teste (categoria + usuário + postagem)
3. Listagem de obras
4. Busca por ID
5. Validação da serialização Pydantic

---

## 📊 Status do Desenvolvimento

| Módulo | Status | Detalhes |
|---|---|---|
| Autenticação (cadastro, login, /me) | ✅ Completo | Controller + Service + Repository + Schemas |
| Obras / Postagens (CRUD) | ✅ Completo | Controller + Service + Repository + Schemas |
| Artistas (listagem e busca) | ✅ Completo | Controller + Service + Repository + Schemas |
| Assistente IA (chatbot n8n) | ✅ Completo | Controller + Service + Repository + Schemas |
| Chat entre usuários | ⚠️ Apenas Models | Faltam Controller, Service, Repository |
| Planos e Assinaturas | ⚠️ Apenas Models | Faltam Controller, Service, Repository |
| Logs de Auditoria | ⚠️ Apenas Model | Faltam Controller, Service, Repository |
| Upload de Arquivos | ⚠️ Parcial | Diretório `uploads/` existe, mas sem endpoint |
| Edição de Perfil | ❌ Não iniciado | Sem endpoint para editar dados do usuário |

---

<p align="center">
  <sub>Artfolio © 2026 — Trabalho de Conclusão de Curso</sub>
</p>
