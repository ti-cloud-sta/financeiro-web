# Padrões de Frontend Angular

Diretrizes e boas práticas para o desenvolvimento no frontend Angular da plataforma.

---

## 1. Arquitetura e Componentização
- **Standalone Components**: Todo novo componente, diretiva ou pipe deve ser standalone por padrão (`standalone: true`).
- **Angular Signals**: Priorizar o uso de Angular Signals (`signal()`, `computed()`, `effect()`) para o gerenciamento de estado reativo local em vez de variáveis mutáveis simples ou dependências desnecessárias de RxJS.
- **Nova Sintaxe de Control Flow**: Utilizar a sintaxe moderna do Angular (@if, @for, @switch) em todos os templates HTML, evitando diretivas legadas (`*ngIf`, `*ngFor`).
- **Separação de Arquivos**: Toda página e componente deve possuir arquivos separados para template (`.html`), estilos (`.scss`) e lógica (`.ts`). É proibido o uso de templates ou estilos inline.
- **Variáveis Globais SCSS**: Para estilos customizados, importe as variáveis globais no arquivo SCSS do componente:
  ```scss
  @import 'styles/variables';
  ```

---

## 2. Reutilização de Componentes (`shared/components/`)
Antes de criar qualquer elemento visual, verifique se ele já existe no diretório `shared/components/`.

### Componentes Padrão Disponíveis:
- `avatar`: Exibição de foto ou iniciais de usuários/colaboradores.
- `badge`: Tags de status, valores e categorias.
- `breadcrumb`: Navegação hierárquica superior.
- `button`: Botões padronizados (`primary`, `secondary`, `outline`, `ghost`, etc.).
- `card`: Contêineres de conteúdo com bordas e cantos arredondados padrão.
- `dropdown`: Menus suspensos de seleção e opções de ação.
- `empty-state`: Estado vazio quando não há registros a exibir.
- `error-state`: Feedback amigável para falhas de carregamento.
- `input`: Campos de texto e formulários padronizados.
- `loading`: Indicadores e spinners de carregamento.
- `modal`: Modais de diálogo e formulários pop-up.
- `skeleton`: Skeleton screens estruturados para pré-carregamento.
- `tooltip`: Dicas de contexto em botões e ícones.

> **ATENÇÃO**: Caso sinta falta de componentes comuns (como tabelas avançadas, switches, datepickers específicos), **pergunte ao usuário** antes de criar do zero ou instalar bibliotecas externas.

---

## 3. Popups, Confirmações e Feedback ao Usuário
- **Proibição de `alert()` e `confirm()`**: É expressamente proibido o uso das funções nativas `alert()` e `confirm()` do navegador.
- **Modal de Confirmação Padrão**: Para alertas, mensagens de sucesso, avisos de erro e confirmações de ações destrutivas (exclusões, cancelamentos), utilize o componente `<app-confirm-modal>` integrado no template HTML da página e controlado via Signals/variáveis no TypeScript.
- **Exibição de Erros Detalhados**: Ao capturar falhas em chamadas HTTP ou processamento, extraia e exiba a mensagem exata retornada pelo backend (normalmente em `err.error?.detail` no FastAPI) em vez de exibir mensagens genéricas como "Erro ao salvar".

---

## 4. Consumo de Streaming em Tempo Real (NDJSON)
- Para processamentos assíncronos longos (como importações em lote de planilhas ou PDFs pesados), o backend retorna `StreamingResponse` com NDJSON (Newline Delimited JSON).
- No frontend, consuma esses endpoints via API nativa do navegador (`fetch` e `response.body.getReader()`), pois o `HttpClient` clássico do Angular tende a bufferizar o stream.
- **Atualização de UI (NgZone)**: O loop de leitura de chunks do stream deve ser envolvido em `this.ngZone.run(() => { ... })` para disparar o Change Detection do Angular imediatamente, mantendo contadores, barras de progresso e spinners fluidos sem congelar a tela.
