# ERP Modular — SantaMaria

> Plataforma ERP moderna, modular e escalável desenvolvida para centralizar e automatizar processos do dia a dia através de módulos independentes.

---

# Visão Geral

O ERP Modular nasceu com o objetivo de ser uma plataforma única para desenvolvimento de diversos módulos de negócio, permitindo que novas funcionalidades sejam adicionadas continuamente sem impactar a estrutura existente.

Diferente de sistemas desenvolvidos para resolver apenas uma necessidade específica, este projeto foi concebido como uma plataforma de longo prazo, preparada para crescer de forma organizada, mantendo alta qualidade de código, facilidade de manutenção e excelente experiência para o usuário.

Todo o desenvolvimento segue princípios modernos de arquitetura de software, priorizando baixo acoplamento, alta coesão e reutilização de componentes.

---

# Tecnologias Utilizadas

## Frontend
* Angular (última versão estável)
* Standalone Components e Angular Signals
* Angular Router, RxJS, SCSS
* Componentização responsiva e Mobile First
* Estrutura preparada para Control Flow (`@if`, `@for`, `@switch`)

## Backend (Mapeado via Auditoria Técnica)
* **Framework Web:** Python, FastAPI e Uvicorn (Arquitetura REST assíncrona)
* **ORM e Validação:** SQLAlchemy, PyMySQL e Pydantic
* **Gerenciamento de Configuração:** Pydantic-Settings (`.env`)
* **Processamento de Dados:** Pandas e OpenPyXL (para leitura em massa de arquivos de Excel)
* **Upload e Files:** Python-Multipart
* **Inteligência Artificial:** SDK `google-genai` (modelo configurável via `GEMINI_MODEL`, default *gemini-3.5-flash-lite*)
* **E-mail:** Gmail API via OAuth 2.0 (envio e leitura de e-mails de cobrança no módulo de Pendências)

## Banco de Dados
* **MySQL** acessado via SQLAlchemy.
* Uso massivo de Foreign Keys e Relacionamentos para garantir a integridade entre as entidades (Empresas, Unidades, Centros de Custo, Colaboradores, Cargos, Categorias e Movimentações).
* Mecanismo de *Connection Pooling* para estabilidade (`pool_recycle`).

---

# Arquitetura e Estrutura do Backend

O backend foi implementado utilizando **Service Layer** aliada ao **Repository Pattern**, desacoplando rotas, lógica de negócios e persistência.

O fluxo de dados segue rigorosamente a estrutura:
`Requisição HTTP → Router → Validação (Pydantic Schema) → Service → Repository → SQLAlchemy Model → Banco de Dados`

```text
backend/app/
├── core/           # Configurações globais (database.py, config.py)
├── models/         # Entidades e mapeamento do banco (Tabelas SQLAlchemy)
├── schemas/        # Contratos de DTO (Pydantic) para in e out da API
├── repositories/   # Isola as queries e interações com o banco
├── services/       # Contém as regras de negócio e integrações complexas
└── routers/        # Controladores e Endpoints REST da aplicação
```

### Endpoints da API REST
Todas as rotas nascem versionadas através do prefixo `/api/v1/`.

* **APIs de Cadastros Base**: `/categorias`, `/empresas`, `/unidades`, `/centros-custo`, `/cargos-colaboradores`. (Rotas CRUD padronizadas).
* **Autenticação (`/auth`, `/auth/google`, `/users`)**: login JWT, cadastro com aprovação do admin, gestão de usuários e conexão OAuth com o Gmail.
* **Colaboradores (`/colaboradores`)**: Além do CRUD, importa a planilha de RH em duas etapas (`/importar/preview` e `/importar/processar`), com anti-duplicidade por CPF, reativação e desligamentos, e expõe o histórico de turnover (`/movimentos`) e os alertas de ghosts em planos de saúde (`/alertas-plano-saude`).
* **Despesas de Viagens (`/despesas-viagens`)**: `/analisar-arquivo` identifica o fornecedor e extrai as despesas por parsers determinísticos ou pelo Gemini (com os domínios reais do banco injetados no prompt); `/confirmar-importacao` grava o lote após a conferência; dashboards e relatório.
* **Plano de Saúde (`/plano-saude` e `/importacoes/plano-saude`)**: parser universal de faturas, confirmação, relatórios e exportações contábeis.
* **Importações (`/importacoes`)**: histórico de importações, Inadimplência (`/inadimplencia/*`: importação via planilha NDJSON e Datasul, kanban, tratativas, e-mails e dashboards), extratores/conciliações por varejista e conciliação de pagamentos.

---

# Integrações e Processamento Avançado (IA e Big Data)

O ERP SantaMaria lida com cargas complexas de dados de duas maneiras exclusivas no backend:

1. **Processamento de Arquivos em Lote (Excel/Pandas)**
As rotas de importação (como a de pendências de inadimplência e a conciliação bancária) usam Pandas internamente para varrer grandes tabelas. Ao longo da leitura, é utilizado um `StreamingResponse` no FastAPI que jorra eventos (NDJSON) progressivos. O Frontend Angular capta esses eventos pela `Web API (fetch / ReadableStream)` para mostrar na tela o andamento instantâneo da importação (Spinners/Steps).

2. **Inteligência Artificial Generativa**
As extrações de faturas (Despesas de Viagens e Plano de Saúde) consomem o *Google Gemini* quando os parsers determinísticos não resolvem o documento. Como medida de segurança contra *alucinações da IA*, o backend constrói dinamicamente um array contendo as categorias e nomes de colaboradores *verdadeiros* cadastrados no banco antes de realizar o envio (`despesas_viagens_parser_service.py` e `ia_service.py`). Assim, o modelo é forçado a mapear as despesas encontradas na fatura associando-as obrigatoriamente a chaves reais do sistema. Em caso de restrição de Cota de API (`429`), o sistema possui mecanismo automático de **Retry Exponencial**.

---

# Segurança e Autenticação (Aviso Crítico)

> **Estado atual:** o backend emite JWT próprio (`/api/v1/auth/login`, validado por `get_current_user` em `app/api/deps.py`) e o frontend usa o `AuthService` real, com o `auth.interceptor.ts` enviando o token em todas as chamadas `HttpClient`. Todos os routers de negócio exigem autenticação: o `main.py` aplica `dependencies=[Depends(get_current_user)]` em cada `include_router`. São públicos apenas `/api/v1/auth`, `/api/v1/auth/google` e o `public_router` de inadimplência (dashboards e leituras `.../publico`, consumidos pelas páginas `/compartilhar/*`). O CORS (`main.py`) segue aberto (`allow_origins=["*"]`, sem credenciais) e deve ser restringido antes da produção.

> **Correção aplicada nesta auditoria:** `backend/app/core/config.py` continha uma senha de banco de dados real hardcoded como valor padrão da classe `Settings` (exposta no histórico do Git). O valor padrão foi removido; **recomenda-se fortemente rotacionar essa senha no MySQL**, já que ela permanece visível em commits antigos.

---

# Ambientes (Produção e Teste)

O mesmo repositório roda em dois ambientes independentes na VPS, no mesmo domínio. O caminho do site define tudo: cada front consome a própria API, que consome o próprio banco.

| Ambiente | Site | API | Swagger | Banco | Branch |
|---|---|---|---|---|---|
| Produção | https://stamaria.cloud/ | `/api/v1` | desligado | `stamariabd` | `main` |
| Teste | https://stamaria.cloud/teste/ | `/teste/api/v1` | https://stamaria.cloud/teste/docs | `stamariabd_dev` | `dev` |

* **Banco de teste**: cópia da produção recriada **toda sexta-feira às 00:00** (`backend/scripts/clonar_banco_dev.sh` + timer systemd). Tudo o que for alterado no teste durante a semana é descartado. Usuários e senhas são os mesmos da produção; o Gmail fica desligado no teste.
* **Identificação visual**: no teste, a navbar fica laranja e exibe o badge "Ambiente de Teste".
* **Fluxo de trabalho**: desenvolver na `dev` → deploy no teste → PR `dev` → `main` → deploy na produção.
* **Regras para o frontend**: não usar caminhos absolutos para recursos do site e passar chaves de sessão por `chaveStorage()` (ver `.agents/rules/padroes-frontend-angular.md`, seção 5).
* **Infraestrutura, instalação e reversão**: `.agents/context/infraestrutura-vps.md`.

---

# Estrutura do Frontend Angular

```text
src/app/
├── core/         # Infraestrutura global: auth, guards, http, interceptors, mock, services
├── shared/       # Componentes visuais genéricos (Botões, Modais, Tabelas, Inputs)
├── layout/       # Estruturas padrão (Header, Sidebar, Footer)
└── pages/        # Domínios de negócio isolados (Despesas de Viagens, Plano de Saúde,
                   # Extratores, Conciliação de Pagamentos, Inadimplência + versão pública,
                   # Configurações e Cadastros, Previsão de Caixa, Home, Login/Cadastro)
```

*Nota: as features de negócio residem em `app/pages/` (não existe `app/modules/`).*

O Frontend possui gerenciamento através de **Angular Signals** (obrigatório em código novo; a adoção nas páginas existentes ainda é parcial) e adota o padrão **Mobile First**, suportando resoluções de desktop até smartphones. O Layout utiliza menus recolhíveis, skeleton loaders e feedbacks em mensagens de `toast` para alta qualidade UX.

**Autenticação no Frontend**: arquitetura *interface-first* — interfaces como `IAuthService` são injetadas via DI (`app.config.ts`). A autenticação (`AuthService`, `UserService`) já é real contra a API; outros serviços de infraestrutura (permissões, módulos, notificações, menu, dashboard da home) ainda apontam para implementações `Mock*` e podem ser trocados sem afetar as demais camadas.

---

# Princípios Arquiteturais e Qualidade de Código

* **SOLID e DRY**: Segregação severa de interfaces no TS e de camadas Repository/Service no Python.
* **Componentização e Reutilização**: Proibição de recriar modais e tabelas soltas; tudo deriva de `shared/components`.
* **Desempenho e Lazy Loading**: Módulos acessados sob demanda na web e banco consultado via pools persistentes.
* **Semântica e Tratamentos de Exceções**: Retornos paginados uniformes (`Items, Page, Size, TotalPages`) na API para facilitar acoplamento no Typescript. Pydantic Models garantem 100% de sanitização nos dados de entrada.

---

# Filosofia do Projeto

Este ERP não é apenas um sistema, mas uma plataforma em constante evolução. Cada módulo deve ser desenvolvido de forma independente, seguindo os mesmos padrões arquiteturais (FastAPI Service Layer no backend, Angular Signals/Standalone no frontend), garantindo consistência, escalabilidade e facilidade de manutenção a longo prazo, evitando soluções improvisadas.


# Histórico de Evolução (Changelog)

## 19/09/2026 - Refatoração UI/UX do Módulo de Inadimplência
* **Design Premium SaaS**: O painel de Inadimplência/Pendências foi inteiramente reconstruído para adequação ao padrão visual moderno (*Edge-to-Edge*).
* **Visão Geral Consolidada**: Criação de um dashboard global que reúne indicadores Financeiros, Logísticos e Comerciais no mesmo lugar.
* **Padronização de Abas**: As abas departamentais (Financeiro, Comercial, Logística) agora compartilham do mesmo padrão estrutural: um painel 'Atual' contendo KPIs e a Grid principal de faturas, e seções de 'Rankings' e 'Evolução' extraídas para cartões Full-Width.
* **Nova Visão por Carteira**: Implementação completa da aba 'Gerente/Representante' no Financeiro, com seletores de carteira e grids de KPIs segmentados.
* **Ações e Histórico**: Integração padronizada do Modal de 'Tratativas e Histórico' em todas as grids de inadimplência.

## 05–06/10/2026 - Ambiente de Teste, Infraestrutura e Documentação
* **Ambiente de Teste completo** em `https://stamaria.cloud/teste/`: frontend e backend da branch `dev` (`docker-compose.dev.yml`) usando o banco `stamariabd_dev` (usuário MySQL `app_dev`, restrito a esse banco).
* **Clone semanal do banco**: `backend/scripts/clonar_banco_dev.sh` + `clone-banco-dev.timer` (sextas, 00:00 Brasília), com trava contra gravação na produção, remoção dos tokens Google no teste e validação de views/contagens.
* **Frontend multiambiente**: build com `--base-href` (`BASE_HREF` no `Dockerfile`); `core/config/ambiente.ts` deriva a URL da API, a sinalização visual (badge + navbar laranja) e o prefixo das chaves de sessão a partir do caminho base. Mapa do Brasil passou a usar caminho relativo.
* **Swagger de teste** em `/teste/docs` via `ROOT_PATH` no backend (`FastAPI(root_path=...)`) e rotas `/docs`/`/openapi.json` no `frontend/nginx.conf`; na produção a documentação segue desligada.
* **Proxy**: timeouts de 300 s e `proxy_buffering off` no nginx do host e do container (corrige o 504 nas análises com IA e o atraso nos eventos NDJSON).
* **VPS**: fail2ban instalado no SSH; manutenção única agendada (atualização de pacotes + reboot pendente do kernel); infraestrutura documentada em `.agents/context/infraestrutura-vps.md`.
* **Documentação**: READMEs (raiz, backend, frontend) e contexto de Despesas de Viagens alinhados ao código real; regra de testes Cypress removida (não há Cypress no projeto); nova regra de caminho base/sessão no frontend; `notas.txt` (com credenciais) retirado do repositório e substituído pelo `notas.local.txt`, ignorado pelo Git.
