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
  - Cypress para testes de integração end-to-end.
- **Backend**:
  - FastAPI (Python 3.11+) com arquitetura em camadas (`routers`, `services`, `repositories`, `models`, `schemas`).
  - SQLAlchemy ORM para modelagem e persistência.
  - Pandas e OpenPyXL para processamento robusto de planilhas e arquivos tabulares.
  - Streaming NDJSON para processamento assíncrono em lote sem travamento da interface.
- **Banco de Dados**:
  - MySQL (`stamariabd`), utilizando Views como fonte única de verdade para regras complexas de negócio.
- **Ambiente & Deploy**:
  - Docker e Docker Compose (`docker-compose.yml`).
