# Contexto do Projeto: ERP SANTAMARIA

Visão geral da arquitetura, propósito e ecossistema do ERP Financeiro da Santa Maria.

---

## 1. Propósito do Sistema
O **ERP SANTAMARIA (financeiro-web)** é uma plataforma integrada de gestão financeira, operacional e de recursos humanos, voltada para:
- Monitoramento de inadimplência e recuperação de créditos.
- Conciliação e auditoria de pagamentos bancários.
- Gestão e auditoria de faturas de planos de saúde e odontológicos.
- Prestação de contas e controle de despesas de viagens corporativas.
- Gestão unificada de colaboradores, unidades, centros de custos e empresas do grupo.

---

## 2. Stack Tecnológica
- **Frontend**:
  - Angular 18+ (Standalone Components, Signals, Control Flow moderno `@if`/`@for`).
  - SCSS com Design System modular inspirado em SaaS modernos (Stripe, Linear, Vercel).
  - ECharts / ngx-echarts para visualizações e gráficos interativos.
  - Flatpickr para seleção de datas e períodos.
- **Backend**:
  - FastAPI (Python 3.11+) com arquitetura em camadas (`routers`, `services`, `repositories`, `models`, `schemas`).
  - SQLAlchemy ORM para modelagem e persistência.
  - Pandas e OpenPyXL para processamento robusto de planilhas e arquivos tabulares.
  - Streaming NDJSON para processamento assíncrono em lote sem travamento da interface.
- **Banco de Dados**:
  - MySQL (`stamariabd`), utilizando Views como fonte única de verdade para regras complexas de negócio.
  - Banco de teste `stamariabd_dev`, clonado da produção toda sexta-feira às 00:00.
- **Ambientes**:

  | Ambiente | Site | API | Banco | Branch |
  |---|---|---|---|---|
  | Produção | `https://stamaria.cloud/` | `/api/v1` | `stamariabd` | `main` |
  | Teste | `https://stamaria.cloud/teste/` | `/teste/api/v1` (Swagger em `/teste/docs`) | `stamariabd_dev` | `dev` |

  Fluxo: desenvolver na `dev` → deploy no teste → PR `dev` → `main` → deploy na produção. Detalhes técnicos em `context/infraestrutura-vps.md`.
- **Ambiente & Deploy**:
  - Docker e Docker Compose: `docker-compose.yml` (produção) e `docker-compose.dev.yml` (teste).
  - Produção: o `.env` fica **na pasta raiz** do checkout `/root/projects/financeiro-web` na VPS (não dentro de `/backend` ou `/frontend`). Teste: `.env` próprio na raiz de `/root/projects/financeiro-web-dev`. No desenvolvimento local, o backend lê `backend/.env` (o `uvicorn` roda de dentro de `backend/`).
  - Deploy da produção:
    ```bash
    cd /root/projects/financeiro-web && git pull
    docker compose up -d --build
    ```
  - Deploy do teste:
    ```bash
    cd /root/projects/financeiro-web-dev && git pull
    docker compose -f docker-compose.dev.yml up -d --build
    ```
