# STAR / ERP Santa Maria — Contexto completo da versão 1 (para iniciar a v2)

> **Para quem lê (assistente de IA numa conversa nova):** este arquivo descreve, com o máximo de detalhe, o sistema que está em produção hoje (v1, repositório `financeiro-web`). O objetivo da próxima conversa é **reconstruir o sistema do zero (v2) em outro repositório**, com mais cuidado de arquitetura e engenharia, **sem tirar a v1 do ar** até a v2 estar pronta. Use este documento como fonte de verdade sobre *o que* o sistema faz e *por quê*; a seção 10 lista o que a v1 faz mal e deve ser evitado na v2.
>
> Gerado em **20/10/2026** a partir do código, do banco local (cópia da produção) e de um levantamento somente leitura da VPS. Nenhum segredo (senha, chave, token) foi registrado aqui.

---

## Sumário
1. [O negócio e quem usa](#1-o-negócio-e-quem-usa)
2. [Ambientes, VPS e deploy](#2-ambientes-vps-e-deploy)
3. [Arquitetura técnica da v1](#3-arquitetura-técnica-da-v1)
4. [Banco de dados](#4-banco-de-dados)
5. [Autenticação, usuários e níveis de acesso](#5-autenticação-usuários-e-níveis-de-acesso)
6. [Módulos (regras de negócio)](#6-módulos-regras-de-negócio)
7. [Integrações externas](#7-integrações-externas)
8. [Rotinas, scripts e operação](#8-rotinas-scripts-e-operação)
9. [Como o usuário (dono do projeto) trabalha](#9-como-o-usuário-dono-do-projeto-trabalha)
10. [Dívidas técnicas e lições para a v2](#10-dívidas-técnicas-e-lições-para-a-v2)
11. [Riscos e pendências em aberto](#11-riscos-e-pendências-em-aberto)
12. [Apêndice A — Todas as rotas da API](#apêndice-a--todas-as-rotas-da-api)
13. [Apêndice B — Esquema completo do banco](#apêndice-b--esquema-completo-do-banco)

---

## 1. O negócio e quem usa

- **Empresa:** Indústria e Comércio Santa Maria Ltda. (fabricante de produtos de limpeza; slogan "Cuidamos da sua casa, como cuidamos da nossa!"). Vende para grandes redes varejistas e atacadistas (Assaí/Sendas, Atacadão, Mateus, Mart Minas, Tenda, Savegnago, Zeferino, Coopercica, Raia/Drogasil, Amazon etc.) por meio de **representantes comerciais**, organizados por **gerentes**.
- **Nome do sistema:** **STAR – Sistemas Integrados Santa Maria** (nos e-mails e na tela de login aparece "Sistemas Integrados"). Internamente o projeto se chama "ERP SANTAMARIA" / `financeiro-web`.
- **Para que serve:** ferramenta interna do **financeiro** para:
  1. **Cobrança/inadimplência** de títulos a receber (o módulo mais usado e mais complexo — "Pendências").
  2. **Plano de saúde e seguro**: auditar faturas de operadoras contra a base de colaboradores e lançar as despesas por pessoa.
  3. **Despesas de viagens**: importar faturas de agências/cartões/locadoras (muitas vezes com IA) e lançar por colaborador/categoria, com dashboards.
  4. **Extratores**: transformar os arquivos de pagamento e de prorrogação enviados pelas redes clientes em planilhas conciliadas com o contas a receber (ACR).
  5. **Conciliação de pagamentos**: cruzar a planilha de liberação com extratos bancários em PDF.
  6. **Cadastros**: colaboradores (base do RH), centros de custo, unidades, empresas, categorias, gerentes/representantes, usuários.
- **Quem usa:** equipe do financeiro (perfil Padrão/Administrador). Desde 20/10/2026 existe o nível **Comercial - Vendas**: gerentes comerciais entram e veem **só a própria carteira** de títulos em atraso.
- **Siglas do negócio:**
  - **ACR** = relatório de Contas a Receber exportado do ERP oficial (**Datasul/TOTVS**). É a planilha "ACR dd.mm.xlsx" importada diariamente como pendências e também usada pelos extratores.
  - **Espécie** do título: `DP` (duplicata), `AD`, `AN`, `PR`, `RJ` (adiantamentos, antecipações, protesto/renegociação etc. — no sistema viram status próprios).
  - **Tipo de pedido:** `PV` (venda), `ER`, `E1`, `PX` (exportação). **Carteira:** `SIM`, `VIN`, `CAR`, `DEV` (devolução), `DES`.
  - **Portador:** código do banco/portador no ERP.
  - **Prorrogação:** cliente renegociou o vencimento.
  - **Ghost / fantasma:** pessoa cobrada na fatura do plano de saúde sem respaldo na base do RH.

---

## 2. Ambientes, VPS e deploy

### 2.1 Ambientes
| Ambiente | Site | API | Banco | Branch | Pasta na VPS |
|---|---|---|---|---|---|
| Produção | `https://stamaria.cloud/` | `/api/v1` | `stamariabd` | `main` | `/root/projects/financeiro-web` |
| Teste | `https://stamaria.cloud/teste/` | `/teste/api/v1` (Swagger em `/teste/docs`) | `stamariabd_dev` | `dev` | `/root/projects/financeiro-web-dev` |
| Local (dev) | `http://localhost:4200` | `http://127.0.0.1:8000/api/v1` | `stamariabd` local (cópia da produção) | qualquer | `C:\Users\JOE\Documents\GitHub\financeiro-web` (Windows) |

### 2.2 Repositórios Git
- **`upstream` = `github.com/ti-cloud-sta/financeiro-web`** → repositório da **empresa**; é de onde a VPS faz `git pull`. Pushes de entrega vão para cá (`git push upstream dev`).
- **`origin` = `github.com/joe-blanca-git/financeiro-web`** → fork pessoal do usuário (não é usado pela VPS).
- Fluxo: desenvolver em `dev` → push `upstream dev` → atualizar o teste → merge `dev`→`main` (PR no GitHub ou merge local + `git push upstream <branch>:main`) → atualizar a produção.
- Commits em português, estilo *conventional commits*: `feat(inadimplencia): ...`, `fix(rh): ...`.

### 2.3 VPS (Hostinger)
| Item | Valor |
|---|---|
| Host | `srv1955604.hstgr.cloud` / domínio `stamaria.cloud` (IPv4 `187.127.7.252`) |
| SO | Ubuntu 26.04.1 LTS, kernel 7.0.x, 1 vCPU, 3,8 GB RAM, **sem swap**, disco 48 GB (~12% usado) |
| Acesso | SSH root (senha) + **Web console da Hostinger** (o usuário usa os dois). Chave SSH `claude-code-leitura-vps` (do assistente, só para leitura; remover quando não precisar) |
| Proteção | UFW (só 22/80/443), fail2ban no SSH, `monarx-agent` (Hostinger) |
| Fuso | host em UTC; backend/MySQL em `America/Sao_Paulo` (-03:00) |

**Containers (Docker Compose, `restart: unless-stopped`):**
| Container | O quê | Porta |
|---|---|---|
| `financeiro-web-frontend-1` | nginx:alpine servindo o Angular de produção; proxy `/api/v1` → backend | `127.0.0.1:8080` |
| `financeiro-web-backend-1` | FastAPI (python:3.12-slim, uvicorn 1 worker) | 8000 interna |
| `financeiro-web-db-1` | MySQL 8.0.46, volume `financeiro-web_db_data`, **atende produção e teste** | `127.0.0.1:3306` |
| `financeiro-web-dev-frontend-dev-1` | Angular de teste (`--base-href /teste/`) | `127.0.0.1:8081` |
| `financeiro-web-dev-backend-dev-1` | backend de teste (`ENVIRONMENT=development`, `ROOT_PATH=/teste`, JWT próprio, **Gmail desligado**) | interna |

- **nginx do host** (`/etc/nginx/sites-available/stamaria.cloud`): HTTPS Let's Encrypt (certbot com renovação automática); `/teste/*` → 8081 (remove o prefixo); `/*` → 8080. Timeouts 300 s e `proxy_buffering off` (necessário para o streaming NDJSON das importações). `client_max_body_size 100M`.
- **`.env` da produção** (raiz do checkout; só nomes): `MYSQL_ROOT_PASSWORD`, `JWT_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_URL` (não repassada ao container). **Teste:** `MYSQL_DEV_PASSWORD`, `JWT_KEY_DEV`, `GEMINI_API_KEY`, `GEMINI_MODEL`.
- Banco: usuários MySQL `root` (`%` e `localhost`, usado pela produção) e `app_dev` (só `stamariabd_dev`). `lower_case_table_names=1`, `time_zone=-03:00`.

### 2.4 Deploy (o usuário executa pelo Web console)
```bash
# Teste
cd /root/projects/financeiro-web-dev && git pull --ff-only && docker compose -f docker-compose.dev.yml up -d --build
# Produção (sempre só backend e frontend, nunca reiniciar o db)
cd /root/projects/financeiro-web && git pull --ff-only && docker compose up -d --build backend frontend
```
- **Ordem obrigatória quando há mudança de banco:** backup → SQL no banco → deploy do código.
- Backup manual antes de SQL na produção:
  ```bash
  docker exec financeiro-web-db-1 sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --routines --triggers --events --set-gtid-purged=OFF --no-tablespaces stamariabd' > /root/backup_stamariabd_$(date +%Y%m%d).sql
  ```
- O assistente **não consegue** fazer push para `main` nem deploy na produção (bloqueado pelo classificador de segurança do Claude Code); o usuário faz isso.

### 2.5 Cópia semanal produção → teste
- `clone-banco-dev.timer` (systemd) toda **sexta 00:00 (Brasília)** roda `backend/scripts/clonar_banco_dev.sh`: `mysqldump --routines` da produção → recria `stamariabd_dev` → apaga `users.refresh_token_google` → valida → reinicia o backend de teste. Log: `/var/log/clone-banco-dev.log`.
- Consequência: qualquer coisa criada só no banco de teste some na sexta.

---

## 3. Arquitetura técnica da v1

### 3.1 Stack
- **Backend:** Python 3.12, FastAPI 0.111, SQLAlchemy 2.0 (ORM síncrono, PyMySQL), Pydantic 2, pandas 3 + openpyxl (planilhas), pypdf (PDF), `google-genai` (Gemini), httpx, PyJWT, passlib/bcrypt.
- **Frontend:** Angular 18.2 (standalone components, Signals, control flow `@if/@for`), Bootstrap 5.3, SCSS próprio "estilo SaaS" (Stripe/Linear), ECharts 6 + ngx-echarts 18, Flatpickr, ng-select, SheetJS `xlsx` (exportações no navegador).
- **Banco:** MySQL 8.0, com **regras de negócio em view e função** (ver 4.3).
- **Infra:** Docker Compose numa VPS única; nginx do host + nginx em cada frontend.

### 3.2 Estrutura do backend (`backend/app`)
```
main.py              # FastAPI app, CORS (*), handlers de erro, include_router com Depends(get_current_user) por router
api/deps.py          # get_current_user (JWT + trava do nível Comercial), get_current_admin_user
core/                # config.py (pydantic-settings, lê backend/.env), database.py, security.py (JWT/bcrypt), links.py (URL do front por ambiente)
routers/             # auth, google_auth, users, categorias, empresas, cargos_colaboradores, colaboradores, centros_custo,
                     # unidades, clientes, comercial, plano_saude, plano_saude_ia (montado dentro de importacoes),
                     # despesas_viagens, importacoes (MONOLITO ~6.200 linhas: pendências, extratores, conciliação, dashboards, compartilhar)
services/            # regras: inadimplencia_service (~2.200 linhas), plano_saude_ia_service, plano_saude_service, ia_service (parsers),
                     # despesas_viagens_parser_service, despesas_viagens_service, colaborador_service, colaborador_import_service,
                     # colaborador_movimento_service, importacao_service, dashboard_service, gmail_service, google_auth_service,
                     # feriado_service, acesso_service, carteira_service, comercial_service, cliente_service, ...
repositories/        # alguns CRUDs (colaborador, alias, categoria, centro de custo, empresa, importacao, unidade, cargo)
models/              # SQLAlchemy (1 arquivo por tabela)
schemas/             # Pydantic
scripts/             # backup_rotina.py (não agendado), clonar_banco_dev.sh, systemd/
```
- Autenticação: `OAuth2PasswordBearer`, JWT HS256 com `sub = iduser`, validade `ACCESS_TOKEN_EXPIRE_MINUTES = 480` (8 h).
- Swagger só com `ENVIRONMENT=development`.
- Importações longas usam **streaming NDJSON** (`StreamingResponse`, um JSON por linha com progresso).

### 3.3 Estrutura do frontend (`frontend/src/app`)
```
app.routes.ts        # login, cadastro, primeiro-acesso, compartilhar/* (públicas) + layout principal (authGuard em canActivate e canActivateChild)
core/
  auth/auth.service.ts      # implementa IAuthService (login, sessão no localStorage, convite)
  interfaces/               # classes abstratas (IAuthService, IMenuService, IModulesService...) providas em app.config.ts
  guards/auth.guard.ts      # login obrigatório; nível comercial_vendas só acessa /minha-carteira
  interceptors/auth.interceptor.ts
  config/ambiente.ts        # deriva apiUrl e prefixo de storage do <base href> (produção vs /teste)
  services/                 # um serviço HTTP por domínio + vários "mock-*" (menu, módulos, permissões, notificações)
  mock/modules.mock.ts      # cards da Home (todos fixos e ativos)
layout/              # main-layout, header (só link Home), sidebar, footer
pages/               # home, auth/{login,register,primeiro-acesso}, inadimplencia (+ components/pages/pendencias),
                     # inadimplencia-publica (CÓPIA da anterior para os links públicos), minha-carteira, plano-saude,
                     # despesas-viagens (+ relatorio-viagens), extratores, conciliacao-pagamentos, previsao-caixa, configuracoes-cadastros
shared/components/   # avatar, badge, breadcrumb, button, card, cargo-modal, colaborador-modal, confirm-modal, dropdown,
                     # empty-state, error-state, input, loading, modal, skeleton, tooltip
```
- Tema claro/escuro (`theme.service.ts`; seletores `[data-theme="dark"]`/`[data-bs-theme="dark"]`).
- O ambiente de teste usa o mesmo build com `--base-href /teste/`; chaves do `localStorage` ganham prefixo `teste_` e aparece faixa "Ambiente de Teste".

### 3.4 Padrões que o usuário aprovou na v1 (manter o espírito na v2)
- Visual SaaS: tabelas sem bordas verticais, valores à direita com `tabular-nums`, badges de status coloridos, skeleton no carregamento, layout *edge-to-edge* com sidebar recolhível (`localStorage.sidebarCollapsed`), abas no topo, painel de filtros.
- Nunca `alert()`/`confirm()` nativos: modal de confirmação próprio. Mostrar ao usuário o `detail` de erro vindo da API.
- Nomes de colaboradores sempre em MAIÚSCULAS; anti-duplicidade de colaborador **só por CPF**.

---

## 4. Banco de dados

### 4.1 Visão por domínio (30 tabelas + 1 view + 1 função)
- **Acesso:** `users`, `roles` (`defatult` [sic] = Padrão, `admin`, `comercial_vendas`), `userrole` (sem PK; sem linha = Padrão), `modulos`, `empresamodulo` (pouco usados).
- **Cadastros:** `empresas` (grupo + fornecedores/operadoras; campo `tipo` ex. "PLANO DE SAUDE"), `unidade` (estabelecimentos: 101 Matriz, 104/106 Filial Linhares), `centrocusto` (PK composta id+codigo), `centroestado`, `categorias` (+ `categorias_aliases`), `tipocolaborador` (= "cargo": 8 Padrão, 9 Gerente Comercial, 10 Representante Comercial — os dois últimos são legado).
- **RH:** `colaboradores` (`snAtivo` S/N, `papel` COMERCIAL/MARKETING usado em despesas), `colaborador_aliases` (aprendizado de nomes), `colaboradoresmovimento` (ATIVACAO/DESATIVACAO + origem), `colaboradorunidade` (não usada).
- **Comercial:** `matrizcliente`, `clientes` (`codigo` = código do emitente no Datasul, `nome_abrev`, `idRepresentante`), `gerente` (`codigo`, `nome`, `idUser`, `obs`), `representantes` (`codigo`, `nome`, `idGerente`, `obs`), `clienterepresentante` (legado, cliente→colaborador; **não usar mais**).
- **Despesas/lançamentos:** `importacoes` (todo arquivo processado; campo `tipo`), `movimentacoes` (lançamento por colaborador/categoria/empresa; `createdAt` = **data de competência**), `turnover_planos_saude` (alertas de ghost).
- **Inadimplência:** `nfpendencias`, `historicopendencia`, `tratativas`, `nfpendencias_mensagens`, `feriados`, `tratativapendencia` (legado, não usada), view `vw_nfpendencias_fase`, função `fn_data_corte_vencimento`.

### 4.2 Valores de `importacoes.tipo` em uso
`PENDENCIAS`, `Importação DATASUL`, `PLANO_SAUDE`, `SEGURO`, `IA_DESPESAS`, `MANUAL_DESPESAS`, `COLABORADORES`, `Conciliação Bancária`, `Composição - <Cliente>` (Atacadão, Sendas, Mateus, Cema, Zeferino, Adição...), `Prorrogação - <Cliente>` (Sendas, Savegnago, Amazon, Zeferino, Droga Raia, Mateus, Cema, Mart Minas, Atacadão...).

### 4.3 Regras que vivem no banco (fonte única de verdade da classificação)
**Função `fn_data_corte_vencimento(p_hoje DATE) RETURNS DATE`** — último dia útil antes da data (volta um dia por vez enquanto for sábado, domingo ou estiver em `feriados`). "Vencido" = `dtVencimento <= fn_data_corte_vencimento(CURDATE())`.

**View `vw_nfpendencias_fase`** — calcula `fase` e `status` de cada `nfpendencias` (primeira regra verdadeira vence); faz `CROSS JOIN (SELECT fn_data_corte_vencimento(CURDATE()) AS dataCorte)`:

| Ordem | Condição | Fase | Status |
|---|---|---|---|
| 1 | `encerrado` S ou P | FINALIZADO | P→PRORROGADO, S→OK |
| 2 | `fase`/`status` manuais preenchidos | o manual | o manual |
| 3 | DP + carteira DEV | LOGISTICA | DEVOLUCAO |
| 4 | DP + PV + sem data de entrega | LOGISTICA | SEM DATA DE ENTREGA |
| 5 | DP + ER + CAR + entregue + saldo < original | FISCAL | COMISSAO |
| 6 | DP + PV + CAR + entregue + saldo < original | COMERCIAL | ACORDO |
| 7 | DP + PV + SIM/VIN + entregue + vencido (data de corte) | FINANCEIRO | ATRASADO |
| 8 | espécie AD / AN / PR / RJ | PENDENCIAS | AD / AN / PR / RJ |
| 9 | DP + PX/ER/E1 sem entrega | PENDENCIAS | EXPORTACAO / MARTINS / MERCADINHO |
| 10 | DP + PV + DES + entregue | PENDENCIAS | DES |
| — | nenhuma | PENDENCIAS | ANALISAR |

- A fase/status mudam **com o passar dos dias** (dependem de `CURDATE()`), sem nenhuma importação.
- A view tem `DEFINER`; ao restaurar backup da produção no MySQL local o definer `root@%` não existe → erro 1449. Correção: recriar a view localmente (`files/recriar_view_pendencias_local.sql`).
- `feriados` é preenchida automaticamente pela **BrasilAPI** (feriados nacionais; ano anterior, atual e próximo) a cada importação de pendências. Feriados municipais não contam (decisão do usuário).

### 4.4 Particularidades e armadilhas do esquema v1
- Dinheiro em `FLOAT(18,2)` (`movimentacoes`, `nfpendencias`) e `DECIMAL` só em `turnover_planos_saude`.
- Charset misto `utf8mb3`/`utf8mb4`; nomes com erros que viraram padrão (`parccela`, `updatedAte`, `defatult`), mistura de camelCase e snake_case.
- FKs faltando: `colaboradores→tipocolaborador`, `colaborador_aliases→colaboradores`, `historicopendencia→nfpendencias`, `colaboradoresmovimento.userCreatedId→users`.
- Cascatas inconsistentes: excluir `importacoes` apaga `movimentacoes` e `nfpendencias` (CASCADE), mas é **bloqueado** por `turnover_planos_saude` (o código apaga os alertas antes) e o código desvincula `nfpendencias` antes para não perdê-las.
- Sem índices em `dtVencimento`, `encerrado`, `dataBaixa` (volume ainda pequeno: centenas de títulos, ~4 mil movimentações, ~1.900 clientes).
- Usuário "sistema" fixo `iduser = 14` assina históricos automáticos.

---

## 5. Autenticação, usuários e níveis de acesso

- **Login:** `POST /auth/login` (e-mail + senha) → JWT. Usuário com `active != 'S'` é bloqueado.
- **Autocadastro** público em `/cadastro` (`POST /auth/register`): cria usuário **inativo** até um admin liberar. O usuário decidiu **manter** essa página.
- **Cadastro por convite (admin)** — implementado em 20/10/2026:
  - Admin informa nome, e-mail e nível → sistema cria senha aleatória (ninguém vê) e envia e-mail de convite **pela conta Google do admin** ("Bem-vindo ao STAR...").
  - Link `.../primeiro-acesso?token=...` válido **8 horas** e de **uso único** (no banco só o hash SHA-256 em `users.convite_token_hash` + `convite_expira_em`).
  - Página de primeiro acesso: senha com ≥ 8 caracteres, número, maiúscula e caractere especial (validado no front e na API); ao salvar já faz login.
  - Ação **Reenviar convite** gera link novo e invalida o anterior. Na v1 serve também como "esqueci minha senha" (não existe recuperação de senha).
  - O link usa o endereço do ambiente (`core/links.py`): produção `https://stamaria.cloud`, teste `https://stamaria.cloud/teste`, local `FRONTEND_URL`.
- **Níveis (roles):**
  | Nível | Valor | Acesso |
  |---|---|---|
  | Administrador | `admin` | tudo + gestão de usuários (`get_current_admin_user`) |
  | Padrão | sem linha em `userrole` (ou `defatult`) | todos os módulos, sem gestão de usuários |
  | Comercial - Vendas | `comercial_vendas` | **só** `/minha-carteira` |
- **Trava do Comercial - Vendas:** central em `deps.get_current_user` — se o usuário é desse nível e a rota não está em `ROTAS_NIVEL_COMERCIAL` (`/api/v1/auth/me`, `/api/v1/comercial/minha-carteira[/...]`) → 403. No front, o `authGuard` redireciona para `/minha-carteira`.
- **Plano do usuário:** criar níveis **por departamento** com a mesma lógica (lista de rotas liberadas no backend + página de destino no guard + dados filtrados pelo usuário do token, nunca por parâmetro). Na v2 isso deve nascer como um **RBAC de verdade** (permissões por módulo/ação), não como lista fixa.

---

## 6. Módulos (regras de negócio)

### 6.1 Home
Cards fixos dos módulos (mock no front, todos ativos): Plano de Saúde, Despesas de Viagens, Extratores, Pendências, Conciliação de Pagamentos, Previsão de Caixa, Configurações e Cadastros.

### 6.2 Pendências / Inadimplência (`/inadimplencia`) — módulo principal
**Navegação:** sidebar *Dashboards*, *Pendências* (Kanban) e *Atualização de Dados* (importações).

**Importação da planilha ACR** (`POST /importacoes/inadimplencia/importar-pendencias`, NDJSON com progresso):
- Lê só a aba **`Resumo`**, mínimo 21 colunas (A–U). Colunas: A Est (→ `unidade.codigo`), B Espécie, C Série, D Título, E Parcela, F Nr Pedcli, G Tipo Pedido, H Cód. Cliente, J Nome Cliente, K Cód. Matriz, L Portador, M Carteira, N Emissão, O Dt Entrega, P Vencimento, T Valor Original, U Saldo. Datas podem vir como serial do Excel.
- Ignora: linha sem espécie (rodapé), sem vencimento, sem cliente, **vencimento posterior à data de corte** (ainda não venceu), duplicadas.
- Cria automaticamente clientes e matrizes novos.
- **Chave do título:** Unidade + Série + Título + Parcela + Espécie + Carteira.
- Título já existente: saldo diferente → atualiza + histórico "Atualização de Saldo"; carteira diferente → atualiza, **limpa fase/status manuais** + históricos; vencimento maior → **prorrogação** (`encerrado='P'`, históricos "Título Prorrogado"/"Resolução"); vencimento diferente (não maior) → ajuste cadastral; estava baixado e voltou → reabre (`encerrado='N'`).
- **Baixa automática por ausência:** títulos abertos (`encerrado='N'`) com vencimento até a data de corte que **não vieram** na planilha → `encerrado='S'`, `dataBaixa=hoje`, `faseOrigemBaixa` = fase da view no momento; histórico "Pendência finalizada". A planilha precisa ser sempre a base completa em aberto.
- Após inserir/atualizar: `db.flush()` → consulta a view → grava histórico com fase/status da view (a view é a fonte da classificação; o Python não recalcula).
- **Importação via API (Datasul):** `POST /importacoes/inadimplencia/importar-pendencias/datasul` com JSON `{"pendencias":[...]}` (mesmos campos), mesma rotina `_processar_linhas_pendencias`, transação única, tipo "Importação DATASUL".
- Antes de processar, sincroniza feriados (BrasilAPI).

**Kanban de Pendências:** colunas por fase (PENDENCIAS, LOGISTICA, FISCAL, COMERCIAL, FINANCEIRO, FINALIZADO). Arrastar muda a fase **manual** (`nfpendencias.fase`, que passa a ter prioridade na view); sair de FINALIZADO exige escolher status. 18 status: ACORDO, AD, AN, ANALISAR, ATRASADO, COMISSAO, DES, DEVOLUCAO, EXPORTACAO, MARTINS, MERCADINHO, OK, PERDAS, PR, PRORROGADO, PROTESTADO, RJ, SEM DATA DE ENTREGA. Filtro de período (padrão "vencidas" = até a data de corte; atalho "Últ. Data de Venc." = janela calculada pela API em `/janela-regra-dia`; mês/semestre/ano/personalizado). Modal de detalhe com **tratativas** (criar/editar), **histórico** (linha do tempo), **mensagens** (e-mails da pendência, estilo chat) e envio de e-mail de cobrança (individual e em lote) **pela conta Gmail do usuário logado**, com sincronização de respostas do cliente via Gmail API.

**Dashboards** (abas): Visão Geral; **Financeiro** (sub-abas *Gerencial* — KPIs vencido/protestado e evolução, ranking de clientes, faixas de atraso, gráfico e grade de **pagos fora do prazo** [`encerrado='S'`, `faseOrigemBaixa='FINANCEIRO'`, `dataBaixa > dtVencimento`] — e *Gerente/Representante* — cards de concentração por carteira, rankings de gerentes/representantes por valor e por quantidade, filtros gerente→representante, grade de títulos em atraso com ações e botão Compartilhar); Logística (sem data de entrega, devolução); Comercial (acordos); Fiscal; Pendências ACR (sub-abas atrasados, protestados, sem data de entrega, devolução, acordo, AN, AD, RJ, PR, variados). "Vencido" nos KPIs = fase FINANCEIRO com vencimento < hoje.

**Compartilhar:** cada dashboard tem botão que envia e-mail (Gmail do usuário) com link para uma **página pública** `/compartilhar/inadimplencia|logistica|comercial|pendencias-acr` (componente `inadimplencia-publica`, sem login — ver risco na seção 11). O compartilhamento da **carteira** (aba Gerente/Representante) envia só mensagem padrão + link para `/minha-carteira` (exige login do gerente) e pré-preenche o e-mail do usuário vinculado ao gerente.

### 6.3 Minha carteira (`/minha-carteira`, nível Comercial - Vendas)
- O gerente vem do **token** (`gerente.idUser = usuário logado`), nunca de parâmetro. Usuário sem gerente vinculado vê aviso.
- Mostra total vencido, total protestado, quantidade e a grade igual à do painel (título, cliente, representante, vencimento, status, qtd de títulos do cliente, valor) com modais de tratativas, mensagens (só o gravado, sem sync Gmail) e histórico.
- Filtro só pelos representantes **da equipe dele**. As rotas de detalhe conferem se o título pertence à carteira (`carteira_service.titulo_da_carteira`).
- Cadeia de dados: título (`nfpendencias.idCliente`) → `clientes.idRepresentante` → `representantes.idGerente` → `gerente.idUser`.

### 6.4 Configurações e Cadastros (`/configuracoes-cadastros`)
Abas: **Acesso** (usuários; só admin), **Colaboradores**, **Categorias**, **Centros de Custo**, **Unidades**, **Empresas**, **Comercial** (Gerentes, Representantes).
- **Acesso:** grade com nível (badge), "CONVITE PENDENTE", ações alterar senha, reenviar convite, nível de acesso (3 opções), bloquear/desbloquear.
- **Colaboradores:** CRUD (exclusão = `snAtivo='N'` + movimento DESATIVACAO). Importação da **planilha do RH** em 2 etapas (`/colaboradores/importar/preview` e `/importar/processar`): *novos* (cria via `ColaboradorService.create_colaborador`, origem `ATUALIZACAO_BASE`), *divergentes* (centro de custo diferente ou reativação; quem está ativo sem ativação do RH aparece como reativado e ganha ATIVACAO), *desligados* (estão ativos e não vieram na planilha → DESATIVACAO). **Modal Turnover:** aba Histórico do RH (movimentos com origem/usuário) e aba Alertas de Planos de Saúde (ghosts, exportável em Excel).
- **Comercial:** Gerentes (código, nome, qtd de representantes, usuário vinculado, observação; vincular/desvincular usuário por e-mail — só admin; um usuário por gerente). Representantes (código, nome, gerente, qtd de clientes; **Atribuir Clientes** grava `clientes.idRepresentante`; cada cliente tem um único representante, marcar transfere).
- Carga inicial de gerentes/representantes/`nome_abrev`/vínculos veio da planilha `files/dim_emitente.xlsx` (dimensão de emitentes do Datasul: `cod_emitente`, `nome_abrev`, `nome_emit`, `nome_matriz`, `cod_rep`, `nome_representante`, `cdn_repres_indir` = código do gerente, `nome_gerente`). Na planilha cada cliente tem um único representante e cada representante um único gerente (exceto `3 - ADM DIRETO`, sem gerente).

### 6.5 Plano de Saúde e Seguro (`/plano-saude`)
- Sidebar: Dashboard, Atualização de Dados, Relatórios. Abas Plano de Saúde e Seguro de Vida. Cards por operadora (Sorriso Odonto, Unimed Capixaba, Unimed Odonto, Unimed Ituverava; seguros Unimed).
- **Importação:** analisar arquivo → tela de conferência (vincular pessoa/corrigir valor) → confirmar. Rotas `/importacoes/plano-saude/universal/analisar` (principal), `sorriso/*`, `unimed-odonto/*` (`analisar`, `confirmar`, `exportar`).
- **Parsers em cascata** (`ia_service.extrair_beneficiarios_pdf_universal`): 8 parsers determinísticos de PDF (Unimed linha única, sufixo de matrícula, seguro de vida, demonstrativo analítico multilinha, coparticipação, responsável, Sorriso fragmentado, genérico) + parser de planilha (col. B titular, C tipo T/D, J valor, P CPF). **Gemini** só se nenhum parser extrair ou se a soma divergir do total impresso (> 1% ou > R$ 1).
- **Resolução da pessoa:** com CPF → só por CPF (nunca cai para nome, por causa de homônimos); sem CPF → tabela de aliases → nome normalizado exato (só em formatos sem CPF). Só colaboradores **ativos**. Ao confirmar, nome divergente vira alias (aprendizado).
- Confirmação grava `importacoes` (tipo PLANO_SAUDE/SEGURO) e `movimentacoes` (categoria Plano de Saúde/Seguro, empresa = operadora, `createdAt` = competência).
- **Ghosts:** na confirmação, gera `turnover_planos_saude` se o colaborador está inativo **ou** sua última ATIVACAO não veio do RH (origens válidas: `IMPORTACAO_EXCEL`, `MANUAL`, `ATUALIZACAO_BASE`; incluir/reativar pela tela do plano grava origem `IMPORTACOES` e conta como sem respaldo).
- **Relatórios:** relatório geral por competência, exportação Excel, layouts contábeis CSV e TXT (largura fixa), conciliação planilha × sistema.

### 6.6 Despesas de Viagens (`/despesas-viagens`)
- Sidebar: Dashboard (abas Visão Geral, Categorias, Comercial/Marketing), Relatório (matriz colaborador × categoria exportável) e Atualização de Dados.
- **Análise de arquivo** (`/despesas-viagens/analisar-arquivo`, NDJSON): identifica o fornecedor e aplica parser — determinísticos para **Kinto, Localiza, OnFly** (fatura e RDV); Gemini com prompt específico para **RDV Santa Maria, DANFE Rosemary, cartão PJ, Tastur, Maiorca, Sem Parar** (pedágio, placa→colaborador); fallback Gemini genérico com 3 tentativas.
- **OnFly (fatura):** leitura por colunas (`extract_text(extraction_mode="layout")`), o colaborador vem só da coluna **Viajante**; aceita qualquer modal; **reembolsos** entram com valor negativo na categoria "Reembolso".
- Conferência editável (itens não encontrados em vermelho, criar colaborador pelo modal com origem MANUAL) → confirmar (tipo `IA_DESPESAS` ou `MANUAL_DESPESAS`; `createdAt` = competência; aprende aliases).
- Dashboards: KPIs, evolução, donuts por categoria/empresa, mapa do Brasil por estado (via centro de custo → `centroestado`), Top 5, butterfly COMERCIAL × MARKETING (campo `colaboradores.papel`).

### 6.7 Extratores (`/extratores`)
Ferramentas por **rede cliente** que cruzam o arquivo enviado pelo cliente com a planilha ACR e devolvem um **Excel formatado** para download; cada execução é registrada em `importacoes`.
- **Pagamentos (composições)** — `POST /importacoes/<cliente>/extrair` (arquivo do cliente + ACR): lê o demonstrativo/remessa de pagamento do cliente (HTML, PDF ou planilha, um layout por cliente) e monta a planilha "Composição de Pagamento" (nota fiscal, parcela, abatimento, valor líquido, total do depósito) conciliada com o ACR. Clientes: Atacadão, Sendas/Assaí, Mateus, Cema, Amazon, Adição, Atakarejo, Sonda, Zeferino. Tipo `Composição - <Cliente>`.
- **Prorrogações** — `POST /importacoes/<cliente>/conciliar` (relatórios de prorrogação do cliente + ACR): identifica as notas com novo vencimento e gera a planilha conciliada. Clientes: Atacadão, Sendas, Mart Minas, Savegnago, Mateus, Droga Raia, Cema, Amazon, Adição, Atakarejo, Sonda, Zeferino. Tipo `Prorrogação - <Cliente>`.
- Toda a lógica está dentro de `routers/importacoes.py` (parsers HTML/PDF por cliente; regras como "NF começando com 0000 → remove dois zeros", "terminando em T → parcela 02"). Na v2, cada cliente deveria virar um *adapter* testado com arquivos de exemplo.

### 6.8 Conciliação de Pagamentos (`/conciliacao-pagamentos`)
- Conciliador financeiro: **Planilha de Liberação** (Excel, aba que começa com "Relatorio Geral", nome do cliente na coluna P = Nome Abrev, valor na coluna R) + **extratos bancários em PDF** (vários) → `POST /importacoes/conciliacao-pagamentos/conciliar-bancos` (NDJSON com etapas; devolve o arquivo conciliado) e `ler-apb`. Histórico de conciliações (tipo "Conciliação Bancária"). Menus "Extratos Bancários" e "Relatórios de Fechamento" são esboços.
- `clientes.nome_abrev` (carregado do Datasul) casa com a coluna Nome Abrev da planilha de liberação — útil para a v2 conciliar por cliente.

### 6.9 Previsão de Caixa (`/previsao-caixa`)
Apenas placeholder ("em construção"), sem regra implementada.

---

## 7. Integrações externas
| Integração | Uso | Como |
|---|---|---|
| **Google OAuth + Gmail API** | Enviar e-mails (cobrança, compartilhar dashboards, convites) **pela conta de quem está logado**; sincronizar respostas de clientes | `routers/google_auth.py`, `services/google_auth_service.py` (popup de autorização, `users.refresh_token_google`), `services/gmail_service.py`. Desligado no ambiente de teste. Não há conta "do sistema" (SMTP não configurado). |
| **Google Gemini** (`google-genai`) | Extração de dados de PDFs de despesas e fallback de planos | `GEMINI_API_KEY`, `GEMINI_MODEL` |
| **BrasilAPI** | Feriados nacionais (`/api/feriados/v1/{ano}`) | `services/feriado_service.py`, gravados em `feriados` |
| **Datasul (TOTVS)** | ERP oficial; origem do ACR e da dimensão de emitentes | Planilhas exportadas + endpoint de carga de pendências via API |

---

## 8. Rotinas, scripts e operação
- **Backup do banco: NÃO existe agendamento.** `backend/scripts/backup_rotina.py` (mysqldump + zip + e-mail SMTP) existe mas não está no cron e não há `SMTP_*`. O usuário faz backups manuais antes de mudanças.
- Limpeza Docker (cron): `docker builder prune` semanal, `docker image prune` diário. `unattended-upgrades` só segurança, **sem reboot automático** (kernel novo exige reinício manual).
- Scripts SQL de mudança ficam em `files/` (não versionados): `carga_clientes_gerentes_representantes.sql`, `usuarios_convite_comercial.sql`, `recriar_view_pendencias_local.sql`. O usuário roda tudo pelo **MySQL Workbench** (atenção ao *safe update mode*: usar `SET SQL_SAFE_UPDATES = 0` em updates/deletes sem chave).
- Desenvolvimento local no Windows: `cd backend && venv\Scripts\python -m uvicorn app.main:app --port 8000` (o `--reload` trava no Windows) e `cd frontend && npx ng serve --port 4200`. Outro projeto do usuário (`nexas`) usa as portas 4200/5090.
- Ideia anotada (`lembrar.txt`): tabela de log de auditoria `log_nfpendencias` (antes/depois em JSON por alteração).

---

## 9. Como o usuário (dono do projeto) trabalha
- Fala português; quer explicações **simples e diretas**, sem jargão, passo a passo e em ordem. Fica perdido quando há muitos scripts soltos — prefere **um arquivo que faz tudo, idempotente** (pode rodar de novo sem quebrar).
- Ele mesmo executa **todo SQL** (Workbench) e os comandos na VPS (Web console). O assistente não edita `.sql` versionados nem altera a VPS sem pedido explícito; análises na VPS são somente leitura.
- Valida tudo **localmente → teste (/teste) → produção**, com usuários reais testando antes da produção.
- Gosta de consistência visual com o que já existe ("igual à grid do dashboard"), dark mode e de ser avisado de riscos de segurança/vazamento (dados de clientes e boletos são sensíveis).
- Pede para fazer **só o que foi pedido**; decisões de negócio ficam com ele (perguntar quando houver ambiguidade).

---

## 10. Dívidas técnicas e lições para a v2
1. **Monólito de rotas:** `routers/importacoes.py` com ~6.200 linhas mistura pendências, extratores de 12 clientes, conciliação, dashboards e compartilhamento; muita regra dentro do router. → v2: módulos por domínio (ex.: `inadimplencia/`, `extratores/<cliente>.py`), router fino, serviço testável.
2. **Regras divididas entre view SQL e Python** (classificação na view, importação no Python, data de corte que já esteve duplicada em 4 lugares). → v2: decidir **um** lugar (preferência: domínio em código testado, com o banco só garantindo integridade) e cobrir com testes.
3. **Sem migrations:** schema alterado à mão por scripts soltos. → v2: Alembic (ou equivalente) versionado; seeds para dados de referência.
4. **Sem testes automatizados** (nem para parsers de PDF/planilha, que quebram quando o fornecedor muda o layout). → v2: suíte com arquivos de exemplo anonimizados por parser/cliente.
5. **Autorização fraca:** só admin × resto; endpoints e páginas **públicas** expõem dados (seção 11); ids mágicos (`iduser=14`, cargos 9/10, roles 1/2). → v2: RBAC por permissão, nenhum dado sem login, links de compartilhamento com token assinado/escopo/expiração.
6. **Modelagem:** dinheiro em FLOAT, charset misto, nomes inconsistentes/typos, FKs faltando, cascatas inconsistentes, `encerrado` S/N/P como texto mágico, fase/status manuais sobrepondo a regra na mesma coluna. → v2: `DECIMAL`, utf8mb4 em tudo, convenção única de nomes, enums/tabelas de domínio, histórico/auditoria como tabela de eventos.
7. **Frontend:** componentes gigantes (1.500+ linhas), **cópia inteira** do módulo de inadimplência para a versão pública (`inadimplencia-publica`), serviços *mock* em produção (menu, módulos, permissões), dados fixos de exemplo em gráfico (ex.: série `[85000,120000,95000,45000]` no painel), estilos de tabela presos dentro de componentes. → v2: componentes de tabela/KPI/modal reutilizáveis, design system central, estado por feature.
8. **E-mail dependente da conta pessoal do usuário** (Gmail OAuth de cada um); sem conta do sistema. → v2: avaliar conta de serviço/SMTP transacional para e-mails do sistema (convites, alertas), mantendo o envio "em nome do usuário" só onde fizer sentido (cobrança).
9. **Operação:** sem backup agendado, sem monitoramento/logs centralizados, fusos diferentes entre host e containers, uvicorn com 1 worker, banco de teste no mesmo MySQL da produção.
10. **Código morto/legado:** `tratativapendencia`, `colaboradorunidade`, `clienterepresentante`, `get_dashboard_visao_geral` definido duas vezes em `inadimplencia_service.py`, `tipocolaborador` 9/10.

---

## 11. Riscos e pendências em aberto (em 20/10/2026)
- 🔴 **Painéis públicos sem login:** `/compartilhar/inadimplencia|logistica|comercial|pendencias-acr` e os endpoints `GET /importacoes/inadimplencia/dashboard/visao-geral|logistica|comercial` mostram **todas** as carteiras; `GET /importacoes/inadimplencia/pendencias/{id}/tratativas|historico|mensagens/publico` expõem detalhes de qualquer título pelo id. Um gerente com o link vê dados dos outros. Combinado com o usuário: tratar em breve.
- 🔴 **Sem backup automático** do banco de produção.
- 🟠 A view e a função de corte dependem do `DEFINER` (problema ao restaurar backups em outro MySQL).
- 🟠 Ambiente de teste é recriado toda sexta a partir da produção: mudanças de banco precisam ir para a produção ou ser reaplicadas.
- 🔴 **Congelamentos da VPS:** a máquina congelou por inteiro (sem ping/SSH/HTTP) em 21/10 02:17, 22/10 ~19:10 e 23/10 18:30 UTC, ociosa e sem nenhum erro nos logs (journald/sysstat simplesmente param). Suspeita: servidor físico da Hostinger (em 17/10 a VPS ficou 46 min fora e o agente QEMU passou a rodar telemetria de hora em hora). Recomendado abrir chamado na Hostinger pedindo migração de node. Em 23/10 foi criado `/etc/sysctl.d/90-reinicio-automatico.conf` (`kernel.panic=10`, `panic_on_oops`, `softlockup_panic`, `hardlockup_panic`, `nmi_watchdog=1`): se o travamento for dentro da VPS, ela reinicia sozinha em segundos. Não há watchdog de hardware virtual na VPS.
- 🟡 SSH root com senha habilitado; kernel aguardando correção da falha "PwnEscape" (CVE-2026-99999) — reiniciar a VPS quando o Ubuntu publicar o kernel corrigido (`/var/run/reboot-required`).
- Em andamento: lançamento do nível Comercial - Vendas na produção (SQL `usuarios_convite_comercial.sql` + deploy), depois níveis por departamento.

---

## Apêndice A — Todas as rotas da API
Prefixo `/api/v1`. "Público" = sem login. Todas as demais exigem JWT (e o nível Comercial - Vendas só passa nas rotas de `minha-carteira` e `auth/me`).


### `/auth`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| POST | `/auth/convite` | `auth.concluir_primeiro_acesso` | sim | Primeiro acesso: grava a senha escolhida, inutiliza o link e já devolve o login. |
| GET | `/auth/convite/{token}` | `auth.consultar_convite` | sim | Primeiro acesso: confere se o link do convite é válido (existe e não expirou). |
| GET | `/auth/google/callback` | `google_auth.callback_google_oauth` | sim | Endpoint público acessado pelo navegador via redirecionamento do Google após o consentimento. |
| POST | `/auth/google/desconectar` | `google_auth.desconectar_google` |  | Desconecta a conta do Google do usuário logado, revogando e limpando o refresh token. |
| GET | `/auth/google/status` | `google_auth.obter_status_conexao` |  | Retorna o status atual da conexão do usuário com a conta Google. |
| GET | `/auth/google/url` | `google_auth.obter_url_autorizacao` |  | Gera a URL de autorização do Google OAuth 2.0 contendo state assinado com o id do usuário. |
| POST | `/auth/login` | `auth.login_user` | sim | Autentica um usuário e retorna um token JWT. |
| GET | `/auth/me` | `auth.get_user_me` |  | Retorna os dados do usuário logado atualmente. |
| POST | `/auth/register` | `auth.register_user` | sim | Registra um novo usuário no sistema. |

### `/cargos-colaboradores`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/cargos-colaboradores` | `cargos_colaboradores.list_cargos_colaboradores` |  |  |
| POST | `/cargos-colaboradores` | `cargos_colaboradores.create_cargo_colaborador` |  |  |
| GET | `/cargos-colaboradores/{id}` | `cargos_colaboradores.get_cargo_colaborador` |  |  |
| PUT | `/cargos-colaboradores/{id}` | `cargos_colaboradores.update_cargo_colaborador` |  |  |
| PATCH | `/cargos-colaboradores/{id}` | `cargos_colaboradores.patch_cargo_colaborador` |  |  |
| DELETE | `/cargos-colaboradores/{id}` | `cargos_colaboradores.delete_cargo_colaborador` |  |  |

### `/categorias`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/categorias` | `categorias.list_categorias` |  |  |
| POST | `/categorias` | `categorias.create_categoria` |  |  |
| GET | `/categorias/{id}` | `categorias.get_categoria` |  |  |
| PUT | `/categorias/{id}` | `categorias.update_categoria` |  |  |
| PATCH | `/categorias/{id}` | `categorias.patch_categoria` |  |  |
| DELETE | `/categorias/{id}` | `categorias.delete_categoria` |  |  |

### `/centros-custo`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/centros-custo` | `centros_custo.read_centros_custo` |  |  |
| POST | `/centros-custo` | `centros_custo.create_centro_custo` |  |  |
| GET | `/centros-custo/{id}` | `centros_custo.read_centro_custo` |  |  |
| PUT | `/centros-custo/{id}` | `centros_custo.update_centro_custo` |  |  |
| DELETE | `/centros-custo/{id}` | `centros_custo.delete_centro_custo` |  |  |

### `/clientes`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/clientes/` | `clientes.get_clientes` |  |  |
| POST | `/clientes/representante/{id_representante}/vincular` | `clientes.vincular_clientes` |  |  |

### `/colaboradores`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/colaboradores` | `colaboradores.list_colaboradores` |  |  |
| POST | `/colaboradores` | `colaboradores.create_colaborador` |  |  |
| GET | `/colaboradores/alertas-plano-saude` | `colaboradores.listar_alertas_plano_saude` |  |  |
| POST | `/colaboradores/importar/preview` | `colaboradores.preview_importacao_colaboradores` |  |  |
| POST | `/colaboradores/importar/processar` | `colaboradores.processar_importacao_colaboradores` |  |  |
| GET | `/colaboradores/movimentos` | `colaboradores.listar_movimentos` |  |  |
| GET | `/colaboradores/{id}` | `colaboradores.get_colaborador` |  |  |
| PUT | `/colaboradores/{id}` | `colaboradores.update_colaborador` |  |  |
| PATCH | `/colaboradores/{id}` | `colaboradores.patch_colaborador` |  |  |
| DELETE | `/colaboradores/{id}` | `colaboradores.delete_colaborador` |  |  |

### `/comercial`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/comercial/gerentes` | `comercial.listar_gerentes` |  |  |
| GET | `/comercial/gerentes/{id_gerente}/usuario` | `comercial.email_usuario_gerente` |  | E-mail do usuário vinculado ao gerente (pré-preenche o modal de compartilhar). |
| PUT | `/comercial/gerentes/{id_gerente}/usuario` | `comercial.vincular_usuario` |  |  |
| DELETE | `/comercial/gerentes/{id_gerente}/usuario` | `comercial.desvincular_usuario` |  |  |
| GET | `/comercial/minha-carteira` | `comercial.minha_carteira` |  | Carteira do gerente vinculado ao usuário logado. O gerente vem do login (token), nunca |
| GET | `/comercial/minha-carteira/titulos/{id_nf}/historico` | `comercial.historico_titulo` |  |  |
| GET | `/comercial/minha-carteira/titulos/{id_nf}/mensagens` | `comercial.mensagens_titulo` |  |  |
| GET | `/comercial/minha-carteira/titulos/{id_nf}/tratativas` | `comercial.tratativas_titulo` |  |  |
| GET | `/comercial/representantes` | `comercial.listar_representantes` |  |  |

### `/despesas-viagens`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| POST | `/despesas-viagens/analisar-arquivo` | `despesas_viagens.analisar_arquivo_despesas` |  |  |
| POST | `/despesas-viagens/confirmar-importacao` | `despesas_viagens.confirmar_importacao_despesas` |  |  |
| GET | `/despesas-viagens/dashboard/comercial` | `despesas_viagens.get_dashboard_comercial` |  |  |
| GET | `/despesas-viagens/dashboard/visao-geral` | `despesas_viagens.get_dashboard_visao_geral` |  |  |
| GET | `/despesas-viagens/relatorio` | `despesas_viagens.get_relatorio_viagens` |  |  |

### `/empresas`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/empresas` | `empresas.list_empresas` |  |  |
| POST | `/empresas` | `empresas.create_empresa` |  |  |
| GET | `/empresas/{id}` | `empresas.get_empresa` |  |  |
| PUT | `/empresas/{id}` | `empresas.update_empresa` |  |  |
| PATCH | `/empresas/{id}` | `empresas.patch_empresa` |  |  |
| DELETE | `/empresas/{id}` | `empresas.delete_empresa` |  |  |

### `/importacoes`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/importacoes` | `importacoes.get_importacoes` |  |  |
| POST | `/importacoes/adicao/conciliar` | `importacoes.conciliar_adicao` |  |  |
| POST | `/importacoes/adicao/extrair` | `importacoes.extrair_adicao` |  |  |
| POST | `/importacoes/amazon/conciliar` | `importacoes.conciliar_amazon` |  |  |
| POST | `/importacoes/amazon/extrair` | `importacoes.extrair_amazon` |  |  |
| POST | `/importacoes/atacadao/conciliar` | `importacoes.conciliar_atacadao` |  |  |
| POST | `/importacoes/atacadao/extrair` | `importacoes.extrair_atacadao` |  |  |
| POST | `/importacoes/atakarejo/conciliar` | `importacoes.conciliar_atakarejo` |  |  |
| POST | `/importacoes/atakarejo/extrair` | `importacoes.extrair_atakarejo` |  |  |
| POST | `/importacoes/cema/conciliar` | `importacoes.conciliar_cema` |  |  |
| POST | `/importacoes/cema/extrair` | `importacoes.extrair_cema` |  |  |
| POST | `/importacoes/conciliacao-pagamentos/conciliar-bancos` | `importacoes.conciliar_bancos` |  |  |
| POST | `/importacoes/conciliacao-pagamentos/ler-apb` | `importacoes.ler_apb_planilha` |  |  |
| GET | `/importacoes/dashboard` | `importacoes.get_dashboard` |  |  |
| GET | `/importacoes/dashboard/analitico` | `importacoes.get_dashboard_analitico` |  |  |
| POST | `/importacoes/drogaraia/conciliar` | `importacoes.conciliar_drogaraia` |  |  |
| GET | `/importacoes/inadimplencia/dashboard/comercial` | `importacoes.get_dashboard_comercial` | sim |  |
| POST | `/importacoes/inadimplencia/dashboard/compartilhar` | `importacoes.compartilhar_dashboard_inadimplencia` |  |  |
| POST | `/importacoes/inadimplencia/dashboard/compartilhar-carteira` | `importacoes.compartilhar_carteira_inadimplencia` |  | Avisa por e-mail que a carteira do gerente está disponível: mensagem padrão + link |
| POST | `/importacoes/inadimplencia/dashboard/compartilhar-comercial` | `importacoes.compartilhar_dashboard_comercial` |  |  |
| POST | `/importacoes/inadimplencia/dashboard/compartilhar-logistica` | `importacoes.compartilhar_dashboard_logistica` |  |  |
| POST | `/importacoes/inadimplencia/dashboard/compartilhar-pendencias-acr` | `importacoes.compartilhar_dashboard_pendencias_acr` |  |  |
| GET | `/importacoes/inadimplencia/dashboard/logistica` | `importacoes.get_dashboard_logistica` | sim |  |
| GET | `/importacoes/inadimplencia/dashboard/visao-geral` | `importacoes.get_dashboard_visao_geral` | sim |  |
| POST | `/importacoes/inadimplencia/importar-pendencias` | `importacoes.importar_pendencias_inadimplencia` |  |  |
| POST | `/importacoes/inadimplencia/importar-pendencias/datasul` | `importacoes.importar_pendencias_datasul` |  | Recebe as pendências de outros sistemas (Datasul) e aplica exatamente as mesmas regras da |
| GET | `/importacoes/inadimplencia/janela-regra-dia` | `importacoes.obter_janela_regra_dia_inadimplencia` |  |  |
| GET | `/importacoes/inadimplencia/pendencias` | `importacoes.listar_pendencias_inadimplencia` |  |  |
| POST | `/importacoes/inadimplencia/pendencias/enviar-email-lote` | `importacoes.enviar_email_lote` |  | Envia um único e-mail de cobrança/aviso referente a múltiplos títulos (lote) utilizando |
| POST | `/importacoes/inadimplencia/pendencias/{id_nf}/enviar-email` | `importacoes.enviar_email_pendencia` |  | Envia um e-mail de cobrança/aviso referente a uma pendência utilizando a conta Gmail |
| PATCH | `/importacoes/inadimplencia/pendencias/{id_nf}/fase` | `importacoes.alterar_fase_pendencia` |  |  |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/historico` | `importacoes.listar_historico_pendencia` |  |  |
| POST | `/importacoes/inadimplencia/pendencias/{id_nf}/historico` | `importacoes.criar_historico_pendencia` |  |  |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/historico/publico` | `importacoes.listar_historico_pendencia_publico` | sim |  |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/mensagens` | `importacoes.listar_mensagens_pendencia` |  | Retorna a conversa completa de e-mails associada à pendência, |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/mensagens/publico` | `importacoes.listar_mensagens_pendencia_publico` | sim |  |
| PATCH | `/importacoes/inadimplencia/pendencias/{id_nf}/status` | `importacoes.alterar_status_pendencia` |  |  |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/tratativas` | `importacoes.listar_tratativas_pendencia` |  |  |
| POST | `/importacoes/inadimplencia/pendencias/{id_nf}/tratativas` | `importacoes.criar_tratativa_pendencia` |  |  |
| GET | `/importacoes/inadimplencia/pendencias/{id_nf}/tratativas/publico` | `importacoes.listar_tratativas_pendencia_publico` | sim |  |
| PUT | `/importacoes/inadimplencia/tratativas/{id_tratativa}` | `importacoes.editar_tratativa_pendencia` |  |  |
| POST | `/importacoes/martminas/conciliar` | `importacoes.conciliar_martminas` |  |  |
| POST | `/importacoes/mateus/conciliar` | `importacoes.conciliar_mateus` |  |  |
| POST | `/importacoes/mateus/extrair` | `importacoes.extrair_mateus` |  |  |
| POST | `/importacoes/plano-saude/sorriso/analisar` | `plano_saude_ia.analisar_plano_saude_sorriso` |  |  |
| POST | `/importacoes/plano-saude/sorriso/confirmar` | `plano_saude_ia.confirmar_importacao_plano_saude_sorriso` |  |  |
| POST | `/importacoes/plano-saude/sorriso/exportar` | `plano_saude_ia.exportar_sorriso_excel` |  |  |
| POST | `/importacoes/plano-saude/unimed-odonto/analisar` | `plano_saude_ia.analisar_plano_saude_unimed_odonto` |  |  |
| POST | `/importacoes/plano-saude/unimed-odonto/confirmar` | `plano_saude_ia.confirmar_importacao_plano_saude_unimed_odonto` |  |  |
| POST | `/importacoes/plano-saude/unimed-odonto/exportar` | `plano_saude_ia.exportar_unimed_odonto_excel` |  |  |
| POST | `/importacoes/plano-saude/universal/analisar` | `plano_saude_ia.analisar_plano_saude_universal` |  | Rota universal para análise de PDFs de planos de saúde, odontológicos e seguros. |
| POST | `/importacoes/savegnago/conciliar` | `importacoes.conciliar_savegnago` |  |  |
| POST | `/importacoes/sendas/conciliar` | `importacoes.conciliar_sendas` |  |  |
| POST | `/importacoes/sendas/extrair` | `importacoes.extrair_sendas` |  |  |
| POST | `/importacoes/sonda/conciliar` | `importacoes.conciliar_atakarejo` |  |  |
| POST | `/importacoes/sonda/extrair` | `importacoes.extrair_atakarejo` |  |  |
| POST | `/importacoes/zeferino/conciliar` | `importacoes.conciliar_zeferino` |  |  |
| POST | `/importacoes/zeferino/extrair` | `importacoes.extrair_zeferino` |  |  |
| DELETE | `/importacoes/{id_importacao}` | `importacoes.excluir_importacao` |  |  |

### `/plano-saude`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/plano-saude/relatorio-geral` | `plano_saude.get_relatorio_geral` |  |  |
| POST | `/plano-saude/relatorio-geral/conciliar` | `plano_saude.conciliar_relatorio_geral` |  |  |
| GET | `/plano-saude/relatorio-geral/contabilidade` | `plano_saude.gerar_relatorio_contabilidade` |  |  |
| GET | `/plano-saude/relatorio-geral/contabilidade-txt` | `plano_saude.gerar_relatorio_contabilidade_txt` |  |  |
| GET | `/plano-saude/relatorio-geral/exportar` | `plano_saude.exportar_relatorio_geral` |  |  |

### `/unidades`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/unidades` | `unidades.read_unidades` |  |  |
| POST | `/unidades` | `unidades.create_unidade` |  |  |
| GET | `/unidades/{id}` | `unidades.read_unidade` |  |  |
| PUT | `/unidades/{id}` | `unidades.update_unidade` |  |  |
| DELETE | `/unidades/{id}` | `unidades.delete_unidade` |  |  |

### `/users`

| Método | Rota | Handler | Público | Descrição |
|---|---|---|---|---|
| GET | `/users` | `users.get_users` |  | Lista todos os usuários. Acesso restrito a administradores. |
| POST | `/users` | `users.criar_usuario_por_convite` |  | Cria o usuário com uma senha aleatória (que ninguém conhece) e envia o convite de |
| PATCH | `/users/{user_id}/admin` | `users.change_user_admin` |  |  |
| POST | `/users/{user_id}/convite` | `users.reenviar_convite` |  | Gera um link novo (o anterior deixa de valer) e reenvia o convite. |
| PUT | `/users/{user_id}/password` | `users.change_user_password` |  |  |
| PATCH | `/users/{user_id}/role` | `users.change_user_role` |  |  |
| PATCH | `/users/{user_id}/status` | `users.change_user_status` |  |  |

## Apêndice B — Esquema completo do banco

Extraído do MySQL local (cópia da produção) em 20/10/2026. Formato: `coluna tipo [PK] [UNI] [NULL] [AI]`; `FK:` lista as chaves estrangeiras (com a regra de exclusão quando não for RESTRICT). O número de linhas dá a ordem de grandeza do volume atual.

```text
## categorias (10 linhas)
  idCategorias int PK AI, nome varchar(50) NULL, descricao varchar(45) NULL, createdAt datetime NULL, updatedAte datetime NULL
## categorias_aliases (4 linhas)
  idcategorias_aliases int PK AI, idCategoria int, alias varchar(45)
  FK: idCategoria->categorias.idCategorias
## centrocusto (61 linhas)
  idCentroCusto int PK AI, codigo int PK, nome varchar(85)
## centroestado (84 linhas)
  idCentroCusto int, estado varchar(200)
  FK: idCentroCusto->centrocusto.idCentroCusto ON DELETE CASCADE
## clienterepresentante (6 linhas)
  idclienterepresentante int PK AI, idCliente int, idRepresentante int
  FK: idCliente->clientes.idclientes; idRepresentante->colaboradores.idColaborador
## clientes (1919 linhas)
  idclientes int PK AI, codigo int NULL, nome varchar(100) NULL, nome_abrev varchar(100) NULL, idMatriz int NULL, idRepresentante int NULL
  FK: idMatriz->matrizcliente.idmatrizCliente; idRepresentante->representantes.idRepresentante
## colaborador_aliases (203 linhas)
  idAlias int PK AI, idColaborador int, nome_divergente varchar(120) UNI, createdAt datetime, updatedAt datetime NULL
## colaboradores (787 linhas)
  nome varchar(80), papel varchar(45) NULL, documento varchar(30) NULL, idColaborador int PK AI, idCargoColaborador int, createdAt datetime, updatedAt datetime NULL, idCentroCusto int, snAtivo varchar(1) NULL
  FK: idCentroCusto->centrocusto.idCentroCusto
## colaboradoresmovimento (933 linhas)
  idcolaboradoresmovimento int PK AI, idColaboradores int, origem varchar(100), userCreatedId int, tipoMovimento varchar(45), createdAt datetime
  FK: idColaboradores->colaboradores.idColaborador ON DELETE CASCADE
## colaboradorunidade (0 linhas)
  idcolaboradorunidade int PK AI, idColaborador int, idUnidade int
  FK: idUnidade->unidade.idUnidade; idColaborador->colaboradores.idColaborador
## empresamodulo (15 linhas)
  idempresamodulo int PK AI, idEmpresas int, idModulos int
  FK: idEmpresas->empresas.idEmpresas; idModulos->modulos.idmodulos
## empresas (16 linhas)
  idEmpresas int PK AI, nome varchar(80), descricao varchar(200) NULL, createdAt datetime NULL, updatedAte datetime NULL, nomeAbrev varchar(100) NULL, tipo varchar(100) NULL
## feriados (42 linhas)
  data date PK, descricao varchar(100) NULL
## gerente (22 linhas)
  idGerente int PK AI, codigo int UNI, nome varchar(100), idUser int UNI NULL, obs varchar(500) NULL
  FK: idUser->users.iduser
## historicopendencia (939 linhas)
  idhistoricopendencia int PK AI, idNfPendencias int NULL, observacao varchar(500) NULL, tipo varchar(45) NULL, createdAt datetime NULL, idUserCreated int NULL, thread_id varchar(100) NULL, message_id varchar(200) NULL, fase varchar(50) NULL, status varchar(50) NULL, dtVencimento date NULL
## importacoes (201 linhas)
  idImportacoes int PK AI, nomeArquivo varchar(200), extensaoArquivo varchar(10), idEmpresa int NULL, createdAt datetime, updatedAte datetime NULL, tipo varchar(45), idUserInc int NULL
  FK: idEmpresa->empresas.idEmpresas; idUserInc->users.iduser
## matrizcliente (621 linhas)
  idmatrizCliente int PK AI, codigo int NULL, nome varchar(100) NULL
## modulos (2 linhas)
  idmodulos int PK AI, Descricao varchar(45) NULL, createdAt datetime NULL, updatedAte datetime NULL
## movimentacoes (4404 linhas)
  idMovimentacoes int PK AI, idCategoria int, idColaborador int, idEmpresa int, idImportacoes int NULL, nrodocumento varchar(100) NULL, valor float(18,2), createdAt datetime, updatedAte datetime NULL, idUnidade int NULL
  FK: idCategoria->categorias.idCategorias; idColaborador->colaboradores.idColaborador; idEmpresa->empresas.idEmpresas; idImportacoes->importacoes.idImportacoes ON DELETE CASCADE; idUnidade->unidade.idUnidade
## nfpendencias (278 linhas)
  idnfpendencias int PK AI, idUnidade int NULL, especie varchar(5) NULL, serie int NULL, titulo varchar(50) NULL, parccela double NULL, nrPedidoCliente int NULL, tipoPedido varchar(45) NULL, idCliente int NULL, idClienteMatriz int NULL, portador int NULL, carteira varchar(45) NULL, dtEmissao date NULL, dtEntrega date NULL, dtVencimento date NULL, valorOriginal float(18,2) NULL, valorSaldo float(18,2) NULL, idImportacoes int NULL, createdAt datetime NULL, encerrado varchar(1) NULL, fase varchar(100) NULL, status varchar(100) NULL, dataBaixa date NULL, faseOrigemBaixa varchar(100) NULL
  FK: idCliente->clientes.idclientes; idClienteMatriz->matrizcliente.idmatrizCliente; idImportacoes->importacoes.idImportacoes ON DELETE CASCADE; idUnidade->unidade.idUnidade
## nfpendencias_mensagens (98 linhas)
  idmensagem int PK AI, idNfPendencias int, mensagem_id varchar(200) NULL, thread_id varchar(100) NULL, de varchar(255), para varchar(500), copia varchar(500) NULL, assunto varchar(255), conteudo longtext, anexos json NULL, dataEnvio datetime NULL, idUserCreated int NULL, minha_mensagem char(1) NULL
  FK: idNfPendencias->nfpendencias.idnfpendencias
## representantes (322 linhas)
  idRepresentante int PK AI, codigo int UNI, nome varchar(100), idGerente int NULL, obs varchar(500) NULL
  FK: idGerente->gerente.idGerente
## roles (3 linhas)
  idRole int PK AI, name varchar(45)
## tipocolaborador (3 linhas)
  idTipoColaborador int PK AI, Nome varchar(45) NULL, Descricao varchar(100) NULL, createdAt datetime NULL, updatedAte datetime NULL
## tratativapendencia (0 linhas)
  idtratativapendencia int PK AI, conteudo varchar(500) NULL, createdAt datetime NULL, idUserCreated int NULL
## tratativas (144 linhas)
  idtratativas int PK AI, conteudo varchar(1000) NULL, createdAt datetime NULL, idCreatedUser int NULL, idNfPendencias int NULL
  FK: idNfPendencias->nfpendencias.idnfpendencias; idCreatedUser->users.iduser
## turnover_planos_saude (54 linhas)
  idTurnoverPlano int PK AI, idColaborador int, idEmpresa int, idImportacao int, competencia varchar(7) NULL, valor decimal(10,2) NULL, resolvido char(1) NULL, createdAt datetime NULL
  FK: idColaborador->colaboradores.idColaborador; idEmpresa->empresas.idEmpresas; idImportacao->importacoes.idImportacoes
## unidade (3 linhas)
  idUnidade int PK AI, codigo int, descricao varchar(50)
## userrole (2 linhas)
  idUser int, idRole int
  FK: idRole->roles.idRole; idUser->users.iduser
## users (8 linhas)
  iduser int PK AI, name varchar(100), email varchar(50), password varchar(1000), active varchar(1) NULL, createdAt datetime NULL, refresh_token_google varchar(1000) NULL, convite_token_hash char(64) NULL, convite_expira_em datetime NULL
## vw_nfpendencias_fase (VIEW)
  idnfpendencias int, titulo varchar(50) NULL, dtVencimento date NULL, createdAt datetime NULL, idCliente int NULL, idClienteMatriz int NULL, especie varchar(5) NULL, carteira varchar(45) NULL, idUnidade int NULL, serie int NULL, parccela double NULL, portador int NULL, dtEmissao date NULL, dtEntrega date NULL, valorOriginal float(18,2) NULL, valorSaldo float(18,2) NULL, fase varchar(100) NULL, status varchar(100) NULL
```
