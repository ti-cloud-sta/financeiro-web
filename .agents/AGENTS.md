# Diretrizes Gerais e Índice de Regras - Projeto SANTAMARIA

Bem-vindo às diretrizes do ERP **SANTAMARIA (financeiro-web)**. Esta documentação estabelece os padrões técnicos, restrições operacionais e regras de negócio para garantir a máxima qualidade, segurança de código e estabilidade do sistema.

A documentação está dividida de forma modular em duas pastas principais:
- **`rules/`**: Regras técnicas e restrições obrigatórias que o assistente de IA deve seguir estritamente.
- **`context/`**: Contexto arquitetural e regras de negócio específicas de cada módulo do ERP.

---

## 🗂️ Índice da Documentação Modular

### 📋 Regras de Desenvolvimento (`.agents/rules/`)
1. [Segurança de Edição de Código e Prevenção de Perda de Dados](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/seguranca-edicao.md)
2. [Padrões de Frontend Angular](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/padroes-frontend-angular.md)
3. [Design System e Padrão Visual SaaS (UI Premium)](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/design-system-ui.md)
4. [Padrões de Backend FastAPI](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/padroes-backend-fastapi.md)
5. [Diretrizes de Banco de Dados e Scripts SQL](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/banco-dados-sql.md)
6. [Integração Contínua, Builds e Testes](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/rules/integracao-ci-testes.md)

### 📚 Contexto e Negócio (`.agents/context/`)
1. [Visão Geral do ERP SANTAMARIA](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/visao-geral-erp.md)
2. [Módulo de Inadimplência e Cobrança](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/modulo-inadimplencia.md)
3. [Módulo de Colaboradores e RH](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/modulo-colaboradores.md)
4. [Módulo de Plano de Saúde e Convênios](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/modulo-plano-saude.md)
5. [Módulo de Despesas de Viagens](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/modulo-despesas-viagens.md)
6. [Módulo de Conciliação de Pagamentos](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/modulo-conciliacao-pagamentos.md)
7. [Estrutura do Banco de Dados MySQL](file:///c:/Users/JOE/Documents/GitHub/financeiro-web/.agents/context/estrutura-banco-dados.md)

---

## 🚨 Regras Mestras Inegociáveis (Resumo Executivo)

### 1. Segurança de Código e Prevenção de Perda de Dados
- **PROIBIDO USO DE SCRIPTS AUTOMATIZADOS PARA EDITAR CÓDIGO**: O assistente JAMAIS deve criar ou rodar scripts externos (Python, Node, Bash, Regex) para cortar, concatenar, substituir ou fatiar arquivos de template HTML, SCSS ou TypeScript. Toda alteração deve ser feita EXCLUSIVAMENTE via ferramentas oficiais (`replace_file_content` ou `multi_replace_file_content`).
- **Edições Cirúrgicas e Pontuais**: Modificações devem ser mínimas e focadas estritamente nas linhas necessárias (5 a 15 linhas). Proibido substituir blocos massivos de centenas de linhas ou sobrescrever arquivos inteiros (`write_to_file` com `Overwrite: true`) para pequenos ajustes visuais.
- **Atenção com Arquivos Longos e Truncamento**: Em arquivos extensos, a visualização inicial do assistente pode truncar o conteúdo. NUNCA assuma o conteúdo faltante. Inspecione o intervalo de linhas exato antes de tocar no código.
- **Localização de Git e Histórico Local**:
  - Git: `C:\Users\JOE\AppData\Local\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`
  - Histórico Local (Timeline): `%APPDATA%\Antigravity IDE\User\History\`
- **Proibição de Arquivos de Teste/Lixo no Repositório**: Nenhum script de teste, arquivo temporário, `.backup`, `.fixed`, dump ou rascunho deve ser deixado no projeto ao encerrar uma resposta.

### 2. Banco de Dados e Arquivos SQL
- **Proibição de Alteração em Arquivos SQL**: O assistente JAMAIS deve modificar arquivos `.sql` (como dumps em `databse/dumps/` ou `files/`). Esses arquivos são apenas backups/referências e toda alteração de schema deve ser executada exclusivamente pelo usuário.
- **Single Source of Truth (Views)**: Regras de Fase e Status residem EXCLUSIVAMENTE no banco de dados através da view `vw_nfpendencias_fase`. O backend nunca deve recalcular essas regras em Python, devendo consultar a view imediatamente após a inserção (usando `db.flush()`).

### 3. Validação de Build e CI
- **Build Obrigatório**: Sempre executar um build de validação (`npm run build` na pasta `frontend/`) e aguardar sua conclusão com sucesso antes de encerrar qualquer macro-tarefa.
- **Testes de Integração**: Após o build válido, executar os testes de integração (`npm run cy:run`) e validar os relatórios antes de finalizar.

### 4. Padrões de Frontend Angular
- Componentes **Standalone** (`standalone: true`).
- **Angular Signals** para gerenciamento de estado reativo local.
- Sintaxe de **Control Flow moderna** (`@if`, `@for`, `@switch`).
- Separação estrita de arquivos (`.html`, `.scss`, `.ts`).
- Reutilização obrigatória dos componentes de `shared/components/` (`avatar`, `badge`, `breadcrumb`, `button`, `card`, `dropdown`, `empty-state`, `error-state`, `input`, `loading`, `modal`, `skeleton`, `tooltip`).
- **Proibição de `alert()` e `confirm()` nativos**: Uso obrigatório de `<app-confirm-modal>`.
- Exibição da mensagem exata de erro retornada pelo servidor (`err.error?.detail`).

### 5. Design System SaaS (UI Premium)
- Visual moderno e corporativo (inspirado em Stripe, Linear, Vercel).
- Layout **Edge-to-Edge** (`.page-container` com `padding: 0;`).
- Barra lateral com sincronização de colapso via `localStorage.getItem('sidebarCollapsed')`.
- Cabeçalho com abas no padrão `.config-layout`, `.dashboard-header` e `.config-nav`.
- Painel de Filtros padronizado com `.filters-panel-card`, selects com largura fixa de `200px`, ordenação alfabética estrita (A-Z) e atalhos rápidos de período.
- Tabelas no padrão SaaS (sem bordas verticais, linhas sutis, valores alinhados à direita com `font-variant-numeric: tabular-nums`).
- Skeleton Loading espelhando a estrutura real em todos os carregamentos.

### 6. Integridade de Regras de Negócio
- **Colaboradores**: Anti-duplicidade estritamente pelo CPF (reativação com movimento de `ATIVACAO` em `colaboradoresmovimento`, proibição de merge por nome), padronização de nomes em caixa alta (Uppercase) via validador Pydantic, e fluxo de criação obrigatório via `ColaboradorService.create_colaborador`.
- **Plano de Saúde**: Filtro estrito de colaboradores ativos (`snAtivo == 'S'`) e aprendizado contínuo de apelidos via `colaboradoralias`.
- **Inadimplência**: Leitura exclusiva da aba `Resumo` na importação, chave composta de unicidade por Unidade+Série+Título+Parcela+Espécie+Carteira, prorrogações marcadas com `encerrado = 'P'` e baixa automática por ausência com `encerrado = 'S'`.
