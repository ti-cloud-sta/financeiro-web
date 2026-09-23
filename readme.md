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
* **Inteligência Artificial:** SDK `google-genai` (Modelo *Gemini-3.5-flash*)

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
* **Colaboradores (`/colaboradores`)**: Além do CRUD, contém rota inteligente `/upload` que varre planilhas complexas, cria vínculos ausentes no banco em tempo real (como Centros de Custo que faltam) e retorna os resultados por stream (`NDJSON`).
* **Importações Inteligentes (`/importacoes`)**: Endpoint `/ia/analise-extrato` dedicado à recepção de faturas (PDF) onde um prompt injeta no Gemini os domínios do banco e força que a IA devolva as despesas classificadas estruturalmente em JSON, seguido pela rota `/ia/salvar` para consolidá-las.

---

# Integrações e Processamento Avançado (IA e Big Data)

O ERP SantaMaria lida com cargas complexas de dados de duas maneiras exclusivas no backend:

1. **Processamento de Arquivos em Lote (Excel/Pandas)**
As rotas de importação (como de colaboradores) usam Pandas internamente para varrer grandes tabelas. Ao longo da leitura, é utilizado um `StreamingResponse` no FastAPI que jorra eventos (NDJSON) progressivos. O Frontend Angular capta esses eventos pela `Web API (fetch / ReadableStream)` para mostrar na tela o andamento instantâneo da importação (Spinners/Steps).

2. **Inteligência Artificial Generativa**
A rota de leitura de extratos consome os serviços do *Google Gemini*. Como medida de segurança contra *alucinações da IA*, o backend constrói dinamicamente um array contendo as categorias e nomes de colaboradores *verdadeiros* cadastrados no banco antes de realizar o envio (`ia_service.py`). Assim, o modelo é forçado a mapear as despesas encontradas na fatura associando-as obrigatoriamente a chaves reais do sistema. Em caso de restrição de Cota de API (`429`), o sistema possui mecanismo automático de **Retry Exponencial**.

---

# Segurança e Autenticação (Aviso Crítico)

> **Estado atual:** o backend emite JWT próprio (`/api/v1/auth/login`, validado por `get_current_user` em `app/api/deps.py`) e o frontend usa o `AuthService` real, com o `auth.interceptor.ts` enviando o token em todas as chamadas `HttpClient`. Todos os routers de negócio exigem autenticação: o `main.py` aplica `dependencies=[Depends(get_current_user)]` em cada `include_router` (só `/api/v1/auth` é público). O CORS (`main.py`) segue aberto (`allow_origins=["*"]`, sem credenciais) e deve ser restringido antes da produção.

> **Correção aplicada nesta auditoria:** `backend/app/core/config.py` continha uma senha de banco de dados real hardcoded como valor padrão da classe `Settings` (exposta no histórico do Git). O valor padrão foi removido; **recomenda-se fortemente rotacionar essa senha no MySQL**, já que ela permanece visível em commits antigos.

---

# Estrutura do Frontend Angular

```text
src/app/
├── core/         # Infraestrutura global: auth, guards, http, interceptors, mock, services
├── shared/       # Componentes visuais genéricos (Botões, Modais, Tabelas, Inputs)
├── layout/       # Estruturas padrão (Header, Sidebar, Footer)
└── pages/        # Domínios de negócio isolados (Despesas de Viagens, Plano de Saúde,
                   # Extratores, Conciliação de Pagamentos, Inadimplência, Home, Login)
```

*Nota: `app/modules/` existe na árvore do projeto mas está vazio — as features de negócio residem em `app/pages/`.*

O Frontend possui gerenciamento através de **Angular Signals** (adotado de forma consistente nas páginas mais recentes; o módulo mais antigo, Despesas de Viagens, ainda não foi migrado) e adota o padrão **Mobile First**, suportando resoluções de desktop até smartphones. O Layout utiliza menus recolhíveis, skeleton loaders e feedbacks em mensagens de `toast` para alta qualidade UX.

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
