# SantaMaria ERP - API REST

API REST desenvolvida em Python 3 com FastAPI para o backend do ERP SantaMaria: cadastros base (empresas, colaboradores, centros de custo, etc.), importação/streaming de planilhas Excel e reconciliação de faturas de clientes/parceiros com apoio de IA generativa (Google Gemini).

## Requisitos

- Python 3.10 ou superior
- MySQL 8.0.46
- `pip` e `venv`

## Instalação

1. Clone o repositório ou navegue até a pasta `backend`.
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração do .env

**Desenvolvimento local:** copie `backend/.env.example` para `backend/.env` (o `uvicorn` é executado de dentro de `backend/`, e o `config.py` lê o `.env` do diretório atual) e preencha as variáveis:

```env
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=stamariabd
DATABASE_USER=seu_usuario
DATABASE_PASSWORD=sua_senha
JWT_KEY=chave_secreta_jwt

# "development" habilita Swagger/ReDoc
ENVIRONMENT=development

# IA Config
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-3.5-flash-lite

# Google OAuth 2.0 (Gmail API — envio/leitura de e-mails de cobrança)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

**Produção (Docker/VPS):** as variáveis vêm do `.env` da **raiz do projeto**, injetadas pelo `docker-compose.yml` (o `.env` do backend não é copiado para a imagem).

**Teste (Docker/VPS):** o `docker-compose.dev.yml` sobe o `backend-dev` com `DATABASE_NAME=stamariabd_dev`, usuário `app_dev`, `JWT_KEY` próprio, Gmail desligado, `ENVIRONMENT=development` e `ROOT_PATH=/teste` (a API fica atrás de `https://stamaria.cloud/teste/`). `ROOT_PATH` é vazio por padrão e só deve ser definido quando a API for servida atrás de um prefixo de caminho.

*Nota: O banco de dados já deve existir conforme a estrutura de tabelas definida em `databse/`. Não há Alembic/migrações — o schema é gerenciado manualmente.*

`GEMINI_API_KEY` é obrigatório apenas para as extrações via IA (`/despesas-viagens/analisar-arquivo` e `/importacoes/plano-saude/*`); sem ele, essas rotas retornam erro explícito, mas o restante da API funciona normalmente. `GEMINI_MODEL` é opcional (default `gemini-3.5-flash-lite`; o parser de Despesas de Viagens usa um modelo fixo definido em `despesas_viagens_parser_service.py`).

## Como Executar a API

Com o ambiente virtual ativado e as variáveis configuradas, execute:

```bash
uvicorn app.main:app --reload
```

A API estará rodando em `http://127.0.0.1:8000`.

## Documentação e Swagger

Disponível apenas com `ENVIRONMENT=development` (em produção `/docs`, `/redoc` e `/openapi.json` ficam desabilitados).

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Ambiente de teste**: [https://stamaria.cloud/teste/docs](https://stamaria.cloud/teste/docs) — o "Try it out" chama a API de teste (`/teste/api/v1`). Autentique pelo `POST /api/v1/auth/login` e use o `access_token` no botão **Authorize**.

## Endpoints Disponíveis

Todos os endpoints seguem o prefixo `/api/v1/`. Os cadastros base seguem CRUD padrão (`GET` lista paginada, `POST`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`, e `PATCH/{id}` na maioria):

- `/auth` (público) — `POST /register` (cria usuário inativo, aguardando aprovação), `POST /login` (JWT), `GET /me`.
- `/auth/google` — OAuth 2.0 do Gmail (`/url`, `/callback`, `/status`, `/desconectar`).
- `/users` (somente admin) — listagem, troca de senha, bloqueio e permissão de admin.
- `/categorias`, `/empresas`, `/cargos-colaboradores`, `/unidades`, `/centros-custo`
- `/clientes` — listagem e vínculo de clientes a representantes (`POST /representante/{id}/vincular`).
- `/colaboradores` — CRUD padrão (DELETE é soft delete: `snAtivo='N'` + movimento `DESATIVACAO`) + importação da planilha de RH em duas etapas (`POST /importar/preview` e `POST /importar/processar`) + `GET /movimentos` (histórico de turnover) e `GET /alertas-plano-saude` (ghosts detectados em faturas).
- `/despesas-viagens` — `POST /analisar-arquivo` (esteira de parsers + IA), `POST /confirmar-importacao`, `GET /dashboard/visao-geral`, `GET /dashboard/comercial`, `GET /relatorio`.
- `/plano-saude` — relatório geral por competência, exportações (Excel, CSV e TXT contábil) e conciliação por planilha.
- `/importacoes` — não é um CRUD simples; concentra:
  - `GET /` (histórico; filtro `categoria` aceita vários tipos separados por vírgula) e `DELETE /{id}`.
  - `GET /dashboard` e `GET /dashboard/analitico` — agregações genéricas de movimentações por `tipo_importacao` (usadas pelo Plano de Saúde).
  - `/inadimplencia/*` — importação de pendências (planilha via **streaming NDJSON** e `POST /importar-pendencias/datasul` em JSON), kanban (fase/status), tratativas, histórico, e-mails via Gmail, dashboards e compartilhamento. Algumas rotas de dashboard e de leitura (`.../publico`) são públicas (`public_router`) para as páginas `/compartilhar/*` do frontend.
  - Rotas de extração/conciliação por cliente/parceiro (composições e prorrogações): `atacadao`, `sendas`, `martminas`, `savegnago`, `mateus`, `drogaraia`, `cema`, `amazon`, `adicao`, `zeferino`, `atakarejo`/`sonda`.
  - `/conciliacao-pagamentos/*` — leitura de planilha APB e cruzamento com extratos bancários (**streaming NDJSON**).
  - `/plano-saude/*` — `universal/analisar` (8 parsers em cascata + fallback IA), `sorriso/*` e `unimed-odonto/*` (análise, confirmação e exportação).

Consulte o Swagger para o contrato completo (schemas de request/response) de cada rota.

## Estrutura do Projeto (Service Layer + Repository Pattern)

```text
backend/app/
├── core/           # Configuração (config.py, database.py)
├── models/         # Entidades SQLAlchemy (tabelas do banco)
├── schemas/        # Contratos Pydantic (request/response)
├── repositories/   # Isola as queries/persistência
├── services/       # Regras de negócio, integrações (dashboard_service.py, ia_service.py)
└── routers/        # Endpoints FastAPI
```

Fluxo de dados: `Requisição HTTP → Router → Schema (Pydantic) → Service → Repository → Model (SQLAlchemy) → MySQL`.

### Modelo de domínio (resumo)

- **Empresa** ↔ **Modulo** (via `EmpresaModulo`): controla quais módulos do ERP cada empresa tem habilitado.
- **Colaborador**: referencia `CargoColaborador` (tabela `tipocolaborador`) e `CentroCusto` (que por sua vez possui N `CentroEstado`).
- **ColaboradorAlias**: mapeia nomes divergentes/abreviados (encontrados em extratos processados por IA) para um `Colaborador` real, evitando duplicidade por erro de digitação/OCR.
- **Movimentacao**: lançamento financeiro individual, sempre vinculado a uma `Importacao` (o lote/arquivo que o originou), e referenciando `Categoria`, `Colaborador` e `Empresa`.

## Integração com IA (Google Gemini)

`app/services/ia_service.py` centraliza o uso do SDK `google-genai`:

- Injeta no prompt as listas reais de categorias/colaboradores cadastrados no banco, forçando a IA a classificar despesas contra chaves que realmente existem no sistema (mitigação de alucinação).
- Usa `response_schema` (Pydantic) para forçar saída estruturada em JSON.
- Possui retry automático (backoff) para erros `429` (quota) e `5xx`/indisponibilidade do serviço.
- Arquivos grandes (>15MB) são enviados via Gemini Files API; menores, inline.
- Uma das análises (Unimed Odonto) é feita sem chamar a IA — puramente por regex + `pypdf` + fuzzy matching (`difflib`).

## Segurança e Autenticação (Aviso Crítico)

> **Estado atual:** a API emite JWT próprio (HS256, validade de 8h, sem refresh) em `POST /api/v1/auth/login`. O `main.py` aplica `dependencies=[Depends(get_current_user)]` em todos os routers de negócio; ficam públicos apenas `/auth`, `/auth/google` e o `public_router` de inadimplência (dashboards e leituras `.../publico` usados pelas páginas compartilhadas). As rotas de `/users` exigem perfil admin (`get_current_admin_user`). O CORS em `main.py` é permissivo (`allow_origins=["*"]`).

Não há testes automatizados (`pytest`) neste backend no momento.
