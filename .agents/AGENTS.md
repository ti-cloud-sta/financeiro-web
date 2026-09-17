# Regras do Projeto SANTAMARIA

- **Proibição de Alteração em Arquivos SQL**: O agente JAMAIS deve modificar arquivos `.sql` (como dumps na pasta `files/` ou `databse/dumps/`). Esses arquivos são apenas exemplos ou backups e toda alteração de banco de dados deve ser feita exclusivamente pelo usuário. Nunca tente atualizar views, tabelas ou scripts SQL.

- **Build de Validação**: Sempre executar um build (`ng build`) ou validação de compilação similar e aguardar sua finalização para garantir que não há erros ANTES de encerrar uma macro-tarefa.

- **Teste de Integração (CI)**: Após a finalização de um build válido, executar os testes de integração ( Comando: `npm run cy:run` ). Aguardar a conclusão e validar os relatórios finais antes de considerar a tarefa concluída.

- **Padrões de Componentes Angular**:
  - Utilizar **Standalone Components** por padrão.
  - Priorizar **Angular Signals** para gerenciamento de estado local.
  - Utilizar a sintaxe de Control Flow do Angular (`@if`, `@for`, `@switch`).
  - Páginas e componentes devem ter arquivos de template (`.html`) e estilo (`.scss`) separados, evitando templates inline.
  - Para estilos customizados, importe as variáveis globais no SCSS: `@import 'styles/variables';`.

- **Reutilização e Componentização (Shared)**:
  - Sempre buscar componentes existentes em `shared/components/` antes de criar novos elementos visuais.
  - Componentes Padrões Disponíveis: `avatar`, `badge`, `breadcrumb`, `button`, `card`, `dropdown`, `empty-state`, `error-state`, `input`, `loading`, `modal`, `skeleton`, `tooltip`.
  - **ATENÇÃO:** Se sentir a falta de algum componente comum (ex: tables, switches, datepickers), **pergunte ao usuário** antes de criar um componente do zero ou de instalar bibliotecas externas.
  - Manter o padrão visual do ERP (Mobile First, responsividade, UI limpa).

- **Arquitetura Modular**:
  - O ERP é modular. Novos fluxos de negócio (módulos) devem ser desenvolvidos de forma independente e isolada.
  - O sistema segue princípios do SOLID, DRY e Clean Code.

- **Design System e Padrão Visual SaaS (UI Premium)**:
  - **Aparência Geral**: O sistema deve transmitir uma estética limpa, corporativa, elegante e moderna (semelhante a Stripe, Linear, Vercel). Evite a aparência de sistemas administrativos antigos. Layouts devem "respirar" e preferir a abordagem "edge-to-edge" no lugar de abrigar tudo dentro de cards pesados.
  - **Tipografia e Hierarquia**: Utilize uma escala tipográfica consistente. Títulos de página em 24px (`1.5rem`) Semibold. Títulos de seção em 16px (`1rem`) Semibold. Textos gerais e auxiliares entre 13px e 14px em tons mutados (`$gray-500` a `$gray-600`).
  - **Espaçamento**: Siga rigidamente um sistema de múltiplos de 4px ou 8px (utilizando `rem`, por exemplo `0.25rem`, `0.5rem`, `1rem`, `1.5rem`, `2rem`).
  - **Cards**: Utilize bordas muito suaves (`1px solid $border-color`), border-radius moderno (`12px`), fundo branco. Evite sombras pesadas em estado de repouso; utilize sombras levíssimas (`box-shadow: 0 4px 12px rgba(0,0,0,0.03)`) atreladas a um leve levante (`transform: translateY(-1px)`) apenas no estado de `:hover`.
  - **Tabelas (SaaS Style)**: Abolição total de bordas verticais. Cabeçalhos de tabela devem ser sutis, em tamanho reduzido (12px), maiúsculas (uppercase), com letter-spacing, usando cores como `$gray-500`. As linhas (`tr`) possuem bordas inferiores super suaves (`$gray-100`) ou fundo branco com hover que escureça levemente o fundo da linha (`rgba($gray-50, 0.5)`). Valores numéricos e financeiros alinham rigidamente à direita com `font-variant-numeric: tabular-nums`.
  - **Botões e Ações**: Evite botões grandes onde uma ação sutil basta. Botões de ação em tabelas devem ser pequenos (ex: 28x28px), sem borda ou fundo preenchido no estado inativo. Cores destrutivas (`$danger`) ou de destaque (`$primary`) devem aparecer idealmente no *hover* (com `background-color` translúcido) para não pesar o visual passivo da tela.
  - **Layout Estrutural de Módulos (Edge-to-Edge)**: 
    - Páginas principais de módulos (como Despesas de Viagens e Plano de Saúde) DEVEM seguir a estrutura fluida de ponta a ponta sem paddings externos matando o layout.
    - **Sidebar Persistence e Padrão**: As páginas principais devem utilizar a estrutura `<aside class="main-sidebar">` e sincronizar seu estado de colapso utilizando `localStorage.getItem('sidebarCollapsed')` no componente TypeScript (`isSidebarCollapsed`), garantindo que o estado da barra lateral se mantenha consistente ao navegar entre os módulos.
    - **Page Container**: A classe `.page-container` deve ter obrigatoriamente `padding: 0;` (e não `padding: 1.5rem 2rem;`) no arquivo SCSS do componente para que o header e as abas grudem perfeitamente nas laterais do container global do ERP.
    - **Cabeçalho com Abas (Dashboard Header)**: Utilize a estrutura HTML baseada em flexbox contendo um contêiner global `.config-layout`. Dentro dele, construa a barra superior horizontal utilizando `<div class="dashboard-header border-bottom">`.
    - **Navegação de Abas (Config Nav)**: Nunca utilize a estrutura padrão de abas `nav-tabs` do Bootstrap isolada. As abas do topo devem ficar dentro de `<ul class="config-nav">`, utilizando `<li class="config-nav-item">` com botões `<button class="config-nav-link" [class.active]="...">`. As classes SCSS deste padrão garantem uma UI premium onde as abas fluem perfeitamente a partir da base do header.
  - **Abas e Navegação**: Opte por abas horizontais limpas com indicador inferior (`border-bottom` de 2px) para a aba ativa, utilizando a cor `$primary`. Remova bordas desnecessárias nas abas inativas.
  - **Inputs, Formulários e Filtros (SaaS Standard)**:
    - **Campos de Texto e Seletores**: Utilizar a classe `.form-control` e `.form-select` para inputs e dropdowns nativos, ou o componente `<app-input>`. A altura padrão de todos os inputs deve ser rigidamente de `38px`, com `border-radius: 8px`. A borda inativa deve ser `$border-color` ou cinza suave. No `:focus`, aplicar borda primária suave (`border-color: rgba($primary, 0.5)`) e anel de foco sutil (`box-shadow: 0 0 0 3px rgba($primary, 0.1)`), anulando o outline do navegador.
    - **Filtros e Busca**: A barra de busca (`.search-box`) deve possuir a lupa alinhada à esquerda de forma absoluta (`left: 0.75rem` ou `1rem`) com o input contendo preenchimento à esquerda (`padding-left: 2.25rem` ou `2.5rem`).
    - **Campos Desabilitados**: Devem ter opacidade de `0.7` e fundo cinza claro (`$gray-100` ou `#f8fafc`).
    - **Conferência de Dados (Tabelas de Conferência)**: As tabelas de conciliação e conferência de importações devem ter apenas linhas horizontais leves, sem bordas verticais, com fonte limpa e alinhamento centralizado para datas e à direita com `font-variant-numeric: tabular-nums` para moedas e valores numéricos.
    - **Painel de Filtros Premium (Dashboard)**:
      - **Container Visual**: Todos os filtros de controle de dados devem ser agrupados dentro de um único card container com a classe `.filters-panel-card` (fundo branco, borda `1px solid rgba($border-color, 0.8)` e cantos arredondados `12px`).
      - **Layout Horizontal Compacto**: Utilizar flexbox no container interno (`.filters-grid` com `display: flex; flex-wrap: wrap; gap: 1.25rem;`) para manter os filtros posicionados sequencialmente sem espaços vazios exagerados.
      - **Largura dos Componentes**: Os selects padrão de filtros (ex: Empresa, Categoria) devem possuir uma largura fixa padrão de `200px` para uma proporção visual consistente.
      - **Ordenação**: Todas as opções dos selectboxes dinâmicos (como Empresas, Pessoas, Categorias) devem ser obrigatoriamente ordenadas em **ordem alfabética (de A a Z)** no frontend via typescript.
      - **Preset de Período**: O filtro de período deve conter o campo de datas inicial e final mais um seletor dropdown (`select` com classe `.shortcut-select`) contendo atalhos rápidos (**Últ. Bimestre**, **Últ. Semestre**, **Este Ano**, **Ano Passado** e **Personalizado**), preenchendo automaticamente o período e aplicando instantaneamente a consulta de dados.
      - **Validação de Data**: DatePickers de período devem aplicar mutualidade de limites (`[maxDate]` na data inicial e `[minDate]` na final) para bloquear seleções inconsistentes.
      - **Skeleton Loading**: Em qualquer recarga/filtro de dados do painel, deve ser exibido um estado de carregamento do tipo skeleton (`app-skeleton` em um contêiner `*ngIf="isDashboardLoading"`) que espelhe o formato e a disposição exata dos cards e gráficos do dashboard real para manter a percepção profissional de performance.
      - **Ações de Página vs Filtros**: Botões de ação direta do dashboard (como "Exportar PDF" ou "Tela cheia") são **ações**, não filtros. Devem ficar localizados na área de cabeçalho da página ou na extremidade direita das abas horizontais de navegação do dashboard (`.dashboard-header`), e nunca misturados no card dos filtros.

- **Integração de Arquivos e Streaming (APIs Assíncronas)**:
  - Para processamento de arquivos tabulares pesados (como planilhas Excel) no backend FastAPI, utilize `pandas` para leitura robusta.
  - Sempre que houver um processamento longo (como validação/importação em lote de dezenas de linhas), **não deixe o frontend pendurado no escuro**. Utilize o `StreamingResponse` do FastAPI retornando NDJSON (Newline Delimited JSON) em *chunks* (`yield`).
  - No Angular (Frontend), consuma esses endpoints de *streaming* NDJSON de forma nativa utilizando a API Web (`fetch` e `response.body.getReader()`), atualizando a UI e mostrando feedback passo-a-passo (com spinners). Evite o `HttpClient` clássico do Angular se ele não suportar o parse do *stream* nativamente sem bufferização integral.

- **Padronização de Grids e Busca**:
  - Toda grid no sistema (especialmente na área de configurações/listagem de cadastros básicos como Colaboradores, Categorias, Centros de Custo, Unidades) deve obrigatoriamente seguir o mesmo padrão de barra de busca.
  - Deve-se utilizar a estrutura HTML `<div class="config-toolbar"><div class="search-box">...</div></div>` separada do `config-header`.
  - A caixa de busca deve refletir o parâmetro para filtro em tempo real (paginação backend) conectando com variáveis como `(ngModelChange)`.

- **Alertas e Confirmações (Popups)**:
  - É expressamente proibido o uso de `alert()` e `confirm()` nativos do navegador em qualquer fluxo do frontend.
  - Para alertas, avisos de erros, mensagens informativas e confirmações de ações (como exclusões, cancelamentos ou exportações), utilize obrigatoriamente o componente `<app-confirm-modal>` integrado no template HTML da página e controlado via sinais/variáveis no TypeScript.
  - **Exibição de Erros Detalhados**: Ao capturar falhas em chamadas HTTP ou de processamento no frontend, extraia e exiba a mensagem de detalhe exata retornada pelo servidor (geralmente em `err.error?.detail` no FastAPI) em vez de exibir mensagens genéricas de falha. Isso garante depuração rápida e transparente.

- **Regras de Negócio e Integridade (Colaboradores e Importações)**:
  - **Prevenção de Duplicidade na Criação**: Ao criar um colaborador (`ColaboradorService.create_colaborador`), o sistema deve verificar se já existe um colaborador inativo **exclusivamente pelo CPF** (documento). Caso exista, ele deve ser atualizado e reativado (`snAtivo = 'S'`), gravando um movimento de 'ATIVACAO', não criando uma linha nova. É proibido mesclar cadastros inativos usando apenas o nome, para evitar a fusão indevida de homônimos.
  - **Padronização de Nomes (Uppercase)**: Todos os nomes de colaboradores devem obrigatoriamente ser salvos em letras MAIÚSCULAS. Isso é garantido no backend através de um `@field_validator` na classe Pydantic `ColaboradorBase`.
  - **Filtro Estrito de Ativos na Conciliação**: Durante as importações de Plano de Saúde e Seguros, os métodos de cruzamento (Regex, Apelidos, Documento) e o envio de base para a Inteligência Artificial devem considerar APENAS colaboradores ativos (`snAtivo == 'S'`).
  - **Fluxo Único de Criação (Camada Service)**: Processamentos em lote (como importação de planilhas) NUNCA devem instanciar e salvar a entidade `Colaborador` diretamente no banco (`self.db.add()`). Toda criação deve ser roteada via `ColaboradorService.create_colaborador` para assegurar que as travas anti-duplicidade, formatação uppercase e gravação de histórico (`ColaboradoresMovimento`) sejam rigorosamente aplicadas.
  - **Aprendizado Contínuo de Apelidos (Aliases)**: Ao corrigir o vínculo de um beneficiário manualmente na tela de conferência de importação de plano de saúde, o backend compara o nome original do PDF com o colaborador escolhido e grava essa divergência na tabela `ColaboradorAlias`, automatizando o reconhecimento inteligente nas próximas faturas.
  - **Importações de Inadimplência (Pendências)**:
    - **Single Source of Truth (Views)**: A lógica de definição de `Fase` e `Status` das pendências deve residir EXCLUSIVAMENTE no banco de dados através da view `vw_nfpendencias_fase`. O backend nunca deve recalcular essas regras em Python, devendo apenas consultar a view imediatamente após a inserção (usando `db.flush()`) para extrair os dados e gerar os históricos de classificação de forma síncrona na importação.
    - **Prorrogações (Resolução de Pendência)**: Ao importar uma planilha, se um título já existir no banco (mesma Unidade, Série, Título e Parcela) e a nova data de vencimento for maior, isso significa que a pendência foi resolvida. O título deve ser prorrogado (atualizar `dtVencimento`), marcado como finalizado (`encerrado = 'S'`) e dois históricos gerados: "Título Prorrogado" e "Pendência finalizada".
    - **Baixa Automática por Ausência**: Títulos que constam no banco como pendentes na competência, mas não vieram na nova importação da planilha, devem ser automaticamente marcados como encerrados (`encerrado = 'S'`) e um histórico de "Pendência finalizada" deve ser gerado assinado pelo usuário do sistema (ex: id 14).
    - **Atualização UI em Tempo Real (NgZone)**: Ao utilizar o `fetch` para consumir o `StreamingResponse` de NDJSON das importações no Frontend, o fluxo de chunks deve ser envolvido em `NgZone.run()` para acionar o Change Detection do Angular e manter barras de progresso ou contadores fluidos na UI sem travar.
    - **Indicadores Visuais**: Pendências com `encerrado = 'S'` entram na fase FINALIZADO e o Kanban deve exibi-las em verde, utilizando ícones de aprovação (check-circle) na UI.
