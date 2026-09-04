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
└── app.routes.ts # rotas raiz (login público + layout protegido por authGuard)
```

> `app/modules/` existe mas está vazio — as features de negócio residem em `app/pages/`.

### Módulos de negócio (`app/pages/`)

| Rota | Página | O que faz |
|---|---|---|
| `home` | Home | Dashboard inicial, módulos ativos, relógio/usuário atual |
| `despesas-viagens` | Despesas de Viagens | Maior módulo do sistema: dashboard (ECharts, mapa por estado, exportação PDF/Excel), upload de extratos com extração via IA, e configurações (CRUD de Colaboradores, Categorias, Centros de Custo, Unidades, Empresas) |
| `extratores` | Extratores | Upload e conciliação de composições/prorrogações por parceiro/varejista (Atacadão, Sendas, Mart Minas, Savegnago, Cema, Mateus, Droga Raia, entre outros) |
| `conciliacao-pagamentos` | Conciliação de Pagamentos | Cruzamento de planilha APB contra extratos bancários, com exportação do resultado |
| `plano-saude` | Plano de Saúde | Extração/confirmação de faturas de planos de saúde (Sorriso via IA, Unimed Odonto via regex), configuração de empresas do módulo |
| `inadimplencia` | Inadimplência | Dashboard e fluxos de atualização de carteira de inadimplentes (dados atualmente mockados) |
| `pages/auth/login` | Login | Formulário reativo (e-mail/senha), autentica via `IAuthService` |

## Camada de dados e HTTP

- Serviços de features (`ColaboradoresService`, `ImportacoesService`, etc.) chamam `HttpClient` diretamente contra `environment.apiUrl`.
- `core/http/http.service.ts` fornece um wrapper genérico (retry com backoff, timeout, tratamento de erro padronizado em português) usado por uma base `BaseApiService<T>` — mas nem todos os serviços de feature o utilizam ainda; parte deles chama `HttpClient` sem passar por essa camada.
- `core/interceptors/auth.interceptor.ts` injeta o `Authorization: Bearer <token>` em toda requisição e implementa refresh de token com fila de requisições concorrentes.

## Autenticação — status atual (placeholder mockado)

O backend (`../backend`) **ainda não implementa autenticação real**. Para não bloquear o desenvolvimento do restante do ERP, o frontend usa uma arquitetura *interface-first*: interfaces abstratas (`IAuthService`, `ISessionService`, `ITokenService`, `IUserService`, `IPermissionsService`, `IModulesService`, `INotificationsService`, `IMenuService`, `IDashboardService`) são registradas em `app.config.ts` apontando para implementações **mock** (`Mock*Service`, em `core/mock/` e `core/services/`).

- `MockAuthService.login()` aceita qualquer e-mail/senha que passe na validação do formulário (não chama o backend) e gera um token fake.
- O `authGuard` libera a navegação com base apenas na presença de um token no `localStorage`.
- Isso é intencional e temporário: quando a autenticação real (ex.: Supabase Auth) for implementada no backend, basta criar as implementações reais (`HttpAuthService`, etc.) e trocar os `useClass` em `app.config.ts` — nenhuma outra parte do app depende diretamente do mock.
- As chamadas de dados de negócio (colaboradores, importações, etc.) **não** são mockadas — usam HTTP real contra o backend.

## Principais dependências

- **UI/Ícones**: Bootstrap 5, Font Awesome (não há kit de componentes como Angular Material/PrimeNG)
- **Gráficos**: `echarts` + `ngx-echarts` (dashboards de Despesas de Viagens)
- **Arquivos**: `xlsx` (Excel), `jspdf` + `html2canvas` (exportação de PDF)
- **Formulários**: `@ng-select/ng-select`, `angularx-flatpickr` (localizado em pt-BR)
- **Datas**: `dayjs`
- Locale global configurado para `pt-BR` (`registerLocaleData(localePt)` em `app.config.ts`)

## Componentes compartilhados (`shared/components/`)

`avatar`, `badge`, `breadcrumb`, `button`, `card`, `cargo-modal`, `colaborador-modal`, `confirm-modal`, `dropdown`, `empty-state`, `error-state`, `input`, `loading`, `modal`, `skeleton`, `tooltip` — todos seguem o padrão de componente standalone com arquivos `.ts`/`.html`/`.scss` separados. Sempre reutilize um componente existente antes de criar um novo (ver `.agents/AGENTS.md` na raiz do repositório para as regras de padrão visual/UX do projeto).

## Gerenciamento de estado

O padrão do projeto é **Angular Signals** (adotado nas páginas mais recentes: `plano-saude`, `extratores`, `inadimplencia`, `conciliacao-pagamentos`, e nos serviços core de tema/layout/sessão). Não há NgRx. O módulo `despesas-viagens` (o mais antigo e maior do sistema) ainda usa propriedades de classe mutadas via `.subscribe()` em vez de signals — candidato a migração futura, mas fora do escopo de uma simples atualização de documentação.
