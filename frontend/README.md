# SantaMaria ERP - Frontend

Frontend Angular do ERP modular SantaMaria. Standalone components, Angular Signals e Control Flow (`@if`/`@for`/`@switch`). Gerado originalmente com Angular CLI 18.2.21.

## Requisitos

- Node.js compatível com Angular 18
- Backend rodando (`../backend`) para as chamadas de API — veja `environments/environment.ts` para a URL configurada (`http://127.0.0.1:8000/api/v1` em desenvolvimento)

## Instalação e execução

```bash
npm install
npm start        # ng serve — http://localhost:4200/
```

Outros scripts: `npm run build` (produção, saída em `dist/`), `npm run watch` (build incremental), `npm test` (Karma/Jasmine), `npm run lint` (ESLint).

## Estrutura (`src/app/`)

```text
app/
├── core/         # auth, guards, http, interceptors, interfaces, models, mock, services, config
├── layout/       # header, sidebar, footer, main-layout
├── pages/        # features do ERP (ver abaixo) + pages.routes.ts
├── shared/       # componentes/diretivas/pipes/validators reutilizáveis
└── app.routes.ts # rotas raiz (login/cadastro, /compartilhar/* públicas e layout protegido por authGuard)
```

> As features de negócio residem em `app/pages/` (não existe `app/modules/`; o alias `@modules/*` do tsconfig está sem uso).

### Módulos de negócio (`app/pages/`)

| Rota | Página | O que faz |
|---|---|---|
| `home` | Home | Página inicial, cards de módulos (via `MockModulesService`), relógio/usuário atual |
| `despesas-viagens` | Despesas de Viagens | Dashboard (ECharts, mapa por estado, butterfly Comercial×Marketing, exportação PDF), relatório matriz (Excel), upload de faturas/RDVs com extração via parsers + IA e conferência antes de salvar |
| `extratores` | Extratores | Composições (pagamentos) e prorrogações por parceiro/varejista (Atacadão, Sendas, Mart Minas, Savegnago, Cema, Mateus, Droga Raia, Amazon, Adição, Zeferino, entre outros) — envia arquivo da empresa + ACR e baixa o Excel gerado |
| `conciliacao-pagamentos` | Conciliação de Pagamentos | Cruzamento de planilha APB contra extratos bancários (streaming NDJSON), com download do resultado |
| `plano-saude` | Plano de Saúde | Dashboard, relatório por competência (exportações Excel/CSV/TXT contábil e conciliação) e importação universal de faturas com conferência |
| `inadimplencia` | Pendências (Inadimplência) | Dashboards por área (Financeiro, Logística, Comercial, Fiscal, Pendências ACR), kanban de pendências com e-mails via Gmail, e atualização de dados (planilha via NDJSON) |
| `configuracoes-cadastros` | Configurações e Cadastros | Usuários (admin), Colaboradores (importação RH e Turnover), Categorias, Centros de Custo, Unidades, Empresas e Comercial (gerentes/representantes) |
| `previsao-caixa` | Previsão de Caixa | Placeholder (ainda sem funcionalidade) |
| `compartilhar/*` | Inadimplência pública | Visualização compartilhada dos dashboards, sem login (`inadimplencia-publica`) |
| `login` / `cadastro` | Login e Cadastro | Formulários reativos; autenticam via `IAuthService` (cadastro fica aguardando aprovação do admin) |

## Camada de dados e HTTP

- Serviços de features (`ColaboradoresService`, `ImportacoesService`, etc.) chamam `HttpClient` diretamente contra `environment.apiUrl` (`http://127.0.0.1:8000/api/v1` em dev; `/api/v1` em produção, com proxy do nginx para o backend).
- `core/interceptors/auth.interceptor.ts` injeta o `Authorization: Bearer <token>` em toda requisição `HttpClient`; em `401` faz logout e em `403` exibe toast e volta para `/home`. Não há refresh token.
- Processamentos longos com streaming NDJSON (importação de pendências e conciliação bancária) usam `fetch` + `ReadableStream` em `importacoes.service.ts`, lendo o token direto do `localStorage` (não passam pelo interceptor).

## Autenticação

Arquitetura *interface-first*: interfaces abstratas são registradas em `app.config.ts` e injetadas via DI.

- **Reais:** `IAuthService` → `AuthService` (`POST /auth/login`, token em `localStorage['erp_access_token']`, usuário em `erp_current_user`, estado via Signals), `IUserService` → `UserService`, `IEnvironmentService`.
- **Ainda mock:** `IPermissionsService`, `IModulesService`, `INotificationsService`, `IMenuService`, `IDashboardService` (`Mock*Service`).
- `authGuard` exige sessão válida (token não expirado); `noAuthGuard` protege login/cadastro.
- `GoogleAuthService` conecta a conta Gmail do usuário (popup OAuth) para envio de e-mails de cobrança no módulo de Pendências.

## Principais dependências

- **UI/Ícones**: Bootstrap 5, Font Awesome (não há kit de componentes como Angular Material/PrimeNG)
- **Gráficos**: `echarts` + `ngx-echarts` (dashboards de Despesas de Viagens, Plano de Saúde e Inadimplência)
- **Arquivos**: `xlsx` (Excel), `jspdf` + `html2canvas` (exportação de PDF)
- **Formulários**: `@ng-select/ng-select`, `angularx-flatpickr` (localizado em pt-BR)
- **Datas**: `dayjs`
- Locale global configurado para `pt-BR` (`registerLocaleData(localePt)` em `app.config.ts`)

## Componentes compartilhados (`shared/components/`)

`avatar`, `badge`, `breadcrumb`, `button`, `card`, `cargo-modal`, `colaborador-modal`, `confirm-modal`, `dropdown`, `empty-state`, `error-state`, `input`, `loading`, `modal`, `skeleton`, `tooltip` — todos seguem o padrão de componente standalone com arquivos `.ts`/`.html`/`.scss` separados. Sempre reutilize um componente existente antes de criar um novo (ver `.agents/AGENTS.md` na raiz do repositório para as regras de padrão visual/UX do projeto).

## Gerenciamento de estado

O padrão do projeto é **Angular Signals** (obrigatório para código novo; ver `.agents/rules/padroes-frontend-angular.md`). Não há NgRx. A adoção ainda é parcial: os serviços core (auth, tema, toast, Google) e páginas como `conciliacao-pagamentos` usam signals de forma ampla, enquanto `inadimplencia`, `configuracoes-cadastros`, `despesas-viagens` e `plano-saude` misturam signals com propriedades de classe e getters.
