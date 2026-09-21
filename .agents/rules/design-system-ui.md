# Design System e Padrão Visual SaaS (UI Premium)

Diretrizes visuais para manter a interface do ERP moderna, elegante, limpa e consistente com os melhores padrões SaaS do mercado (Stripe, Linear, Vercel).

---

## 1. Princípios Visuais Gerais
- **Estética Corporativa Moderna**: Evite a aparência de sistemas legados ou corporativos antigos. Prefira layouts arejados, fluidos e "edge-to-edge" em vez de aninhar elementos em cards pesados desnecessários.
- **Tipografia e Hierarquia**:
  - Títulos de página / cabeçalhos principais: `24px` (`1.5rem`), Semibold.
  - Títulos de seção / painéis: `16px` (`1rem`), Semibold.
  - Textos de apoio, legendas e rótulos: entre `13px` e `14px`, em tons mutados (`$gray-500` a `$gray-600`).
- **Sistema de Espaçamento**: Múltiplos rígidos de 4px ou 8px (usando unidades relativas `rem`, como `0.25rem`, `0.5rem`, `1rem`, `1.5rem`, `2rem`).
- **Cards e Sombras**:
  - Bordas muito suaves: `1px solid $border-color` ou `rgba($border-color, 0.8)`.
  - Cantos arredondados modernos: `12px` (ou `8px` em subcomponentes).
  - Fundo branco limpo.
  - Evite sombras pesadas em estado de repouso. No máximo uma sombra levíssima (`box-shadow: 0 4px 12px rgba(0,0,0,0.03)`) com levante sutil (`transform: translateY(-1px)`) apenas no `:hover`.

---

## 2. Tabelas e Exibição de Dados (SaaS Table)
- **Sem Bordas Verticais**: Abolição total de linhas verticais entre colunas. Apenas bordas horizontais suaves (`$gray-100`).
- **Cabeçalhos Sutis**: Fonte reduzida (`12px`), maiúsculas (`text-transform: uppercase`), com espaçamento entre letras (`letter-spacing: 0.05em`) e cor neutra secundária (`$gray-500`).
- **Efeito Hover**: Escurecimento leve e agradável da linha ao passar o mouse (`background-color: rgba($gray-50, 0.5)`).
- **Alinhamento e Formatação Numérica**: Valores financeiros, percentuais e quantidades devem alinhar rigidamente à direita com `font-variant-numeric: tabular-nums` para que os dígitos fiquem perfeitamente alinhados verticalmente.
- **Botões de Ação na Tabela**: Botões minimalistas e compactos (ex: 28x28px), sem borda ou fundo no estado inativo (`.btn-light.text-secondary.border-0`), exibindo apenas ícones do FontAwesome. Destaques destrutivos (`$danger`) ou de ação devem surgir preferencialmente no *hover*.

---

## 3. Layout Estrutural Edge-to-Edge
Páginas principais de módulos (ex: Inadimplência, Despesas de Viagens, Plano de Saúde) devem seguir a estrutura fluida de ponta a ponta:
- **Container Global**: A classe `.page-container` deve conter obrigatoriamente `padding: 0;` no SCSS do componente para que o header e as abas alcancem as extremidades do container global do ERP.
- **Barra Lateral (Sidebar Persistence)**: Utilizar `<aside class="main-sidebar" [class.collapsed]="isSidebarCollapsed">` e sincronizar o estado no componente via `localStorage.getItem('sidebarCollapsed')` para preservar o colapso entre módulos.
- **Cabeçalho com Abas (Dashboard Header)**:
  ```html
  <div class="config-layout">
    <div class="dashboard-header border-bottom">
      <ul class="config-nav">
        <li class="config-nav-item">
          <button class="config-nav-link" [class.active]="activeTab === 'visao-geral'">Visão Geral</button>
        </li>
      </ul>
    </div>
  </div>
  ```
  *(Nunca utilizar abas padrão `nav-tabs` do Bootstrap isoladas sem esse padrão)*.

---

## 4. Painel de Filtros Premium
Todos os controles e filtros de consulta de dados devem seguir o padrão unificado:
- **Container Visual**: Agrupados dentro de um único card com a classe `.filters-panel-card` (fundo branco, borda suave de 1px e `border-radius: 12px`).
- **Layout Horizontal Compacto**: Container interno com classe `.filters-grid` (`display: flex; flex-wrap: wrap; gap: 1.25rem;`).
- **Largura dos Componentes**: Dropdowns padrão de filtros (Empresa, Categoria, Unidade) devem ter largura fixa padronizada de **`200px`**.
- **Ordenação Alfabética Estrita**: Todas as opções dos selectboxes dinâmicos (Empresas, Colaboradores, Categorias, Status) devem vir ordenadas alfabeticamente de **A a Z** no TypeScript.
- **Preset de Atalhos de Período**: O filtro de datas deve possuir campos de data inicial e final acompanhados de um select com classe `.shortcut-select` contendo os atalhos rápidos (**Últ. Bimestre**, **Últ. Semestre**, **Este Ano**, **Ano Passado**, **Personalizado**), preenchendo as datas e aplicando a consulta instantaneamente.
- **Mutualidade de Limites de Data**: O DatePicker inicial deve ter `[maxDate]="dataFim"` e o final `[minDate]="dataInicio"` para bloquear períodos inconsistentes.
- **Ações de Página vs Filtros**: Botões de ação (ex: "Exportar PDF", "Tela Cheia", "Novo Cadastro") pertencem ao cabeçalho da página (`.dashboard-header`), **nunca** misturados no card dos filtros.

---

## 5. Dashboards Departamentais (SaaS Layout)
- **Aba Visão Geral**: Módulos complexos possuem uma aba "Visão Geral" consolidando os principais KPIs de todas as áreas envolvidas.
- **Painel Atual (.dash-kpi-panel)**: Utilizado nas abas departamentais para agrupar os KPIs do dia/mês atual e a **Tabela Principal (Grid)** de pendências/registros associados.
- **Gráficos e Rankings (Full-Width)**: Gráficos evolutivos (ECharts) e tabelas de ranking devem ficar **fora** do `.dash-kpi-panel`, em contêineres `.row` utilizando `.dash-chart-card.h-100` para ocupar a largura integral com harmonia visual.
- **Skeleton Loading Estruturado**: Ao carregar ou filtrar dados, exibir um estado `app-skeleton` que espelhe com precisão milimétrica a disposição e formato dos cards e tabelas reais da tela.

---

## 6. Padronização de Grids e Busca
Toda listagem e grid de cadastros básicos deve utilizar a barra de busca padronizada separada do header:
```html
<div class="config-toolbar">
  <div class="search-box">
    <i class="fa-solid fa-search text-muted position-absolute" style="left: 1rem; top: 50%; transform: translateY(-50%);"></i>
    <input type="text" class="form-control" placeholder="Buscar..." [(ngModel)]="termoBusca" (ngModelChange)="onBuscaChange()" style="padding-left: 2.5rem; height: 38px; border-radius: 8px;">
  </div>
</div>
```
