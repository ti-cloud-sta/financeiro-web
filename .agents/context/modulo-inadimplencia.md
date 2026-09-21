# Contexto de Negócio e Técnico: Módulo de Inadimplência

Regras de negócio, arquitetura de views, fluxos de conciliação de planilhas e comportamento da interface Kanban de Inadimplência.

---

## 1. Importação de Planilhas de Pendências (`InadimplenciaService`)

### Aba Única de Leitura (`Resumo`):
- O método `importar_pendencias` deve ler estritamente a aba denominada `Resumo` (`sheet_name="Resumo"`). Nenhuma outra aba da planilha deve ser lida ou considerada.

### Identificação e Chave Composta de Unicidade:
- A pendência é identificada combinando a tupla:
  `Unidade + Série + Título + Parcela + Espécie + Carteira`
- Um mesmo título e parcela pode conter linhas diferentes com espécies distintas (ex: `DP` e `AD`) ou carteiras distintas. Essas linhas coexistem como registros independentes no banco de dados, sem colisão ou sobrescrita mútua.

---

## 2. Views como Fonte Única de Verdade (Single Source of Truth)
- A lógica de definição de `Fase` e `Status` das pendências reside **exclusivamente no banco de dados** através da view `vw_nfpendencias_fase`.
- O backend jamais recalcula essas regras em Python.
- **Proibição de Alterar Scripts SQL**: O assistente não edita arquivos `.sql`. Ajustes nas regras de fase devem ser fornecidos ao usuário para execução manual no MySQL.
- Fluxo de persistência:
  1. O backend insere ou atualiza o registro na tabela `nfpendencias`.
  2. Executa `db.flush()`.
  3. Consulta a view `vw_nfpendencias_fase` pelo ID inserido para obter os valores calculados de fase e status.
  4. Salva os registros síncronos na tabela `historicopendencia`.

---

## 3. Comportamento em Reimportações de Planilhas
Quando um título já cadastrado reaparece em uma nova importação:
- **Alteração de Saldo**: Se `valorSaldo` divergir (amortização/abatimento), atualiza o saldo e gera um histórico de *"Atualização de Saldo"*.
- **Alteração de Carteira**: Se a coluna `carteira` (coluna M) divergir, atualiza o campo, limpa os campos manuais `fase` e `status` para `None` (permitindo que a view recalcule automaticamente) e gera históricos de *"Atualização de Carteira"* e *"Classificação"*.
- **Ajuste de Vencimento**: Se a data de vencimento for alterada sem caracterizar prorrogação (`venc_excel != venc_db`), atualiza a data com histórico cadastral.
- **Prorrogações**: Se a nova data de vencimento for maior que a anterior (`venc_excel > venc_db`), considera-se título prorrogado:
  - Atualiza `dtVencimento`.
  - Marca `encerrado = 'P'`.
  - Gera dois históricos: *"Título Prorrogado"* e *"Resolução"*.
- **Retorno de Título (Reabertura)**: Se uma pendência constava como `encerrado = 'S'` por ausência em importação prévia e retorna na planilha atual, seu status é revertido para `encerrado = 'N'`.
- **Baixa Automática por Ausência (Rastreamento por ID)**:
  - Durante o processamento da planilha, todos os IDs encontrados são acumulados em uma lista (`ids_processados_planilha`).
  - Títulos ativos no banco (`encerrado = 'N'`) que não constarem no novo arquivo são marcados automaticamente com `encerrado = 'S'`, gerando o histórico *"Pendência finalizada"* (assinado pelo usuário sistema, id 14).
  - A checagem por ID impede baixas indevidas cruzadas entre diferentes espécies do mesmo título.

---

## 4. Comportamento da Interface Kanban e Dashboards

### Drag & Drop com Interceptação de Fases:
- Quando um card é arrastado da coluna "FINALIZADO" para outra fase (coluna), o frontend intercepta a ação e abre obrigatoriamente o modal `pendencia-detalhe-modal`.
- O usuário deve selecionar um "Novo Status" neste modal antes de persistir o movimento.

### Lista de 19 Opções Padronizadas de Status:
Todos os select boxes de status (filtro Kanban, modal de detalhes e modal de mudança de fase) utilizam a constante estática e alfabética `STATUS_OPTIONS`:
```typescript
[
  "ACORDO", "AD", "AN", "ANALISAR", "ATRASADO", "CART-DES", "COMISSAO", 
  "DES", "DEVOLUCAO", "EXPORTACAO", "MARTINS", "MERCADINHO", "OK", 
  "PERDAS", "PR", "PRORROGADO", "PROTESTADO", "RJ", "SEM DATA DE ENTREGA"
]
```

### Toggles e Cores de Exceção no Kanban:
- **Coluna Logística**: Toggle laranja (`switch-orange`) para mostrar/ocultar títulos com status `DEVOLUCAO` (cor `orange`).
- **Coluna Financeiro**: Toggle vermelho (`switch-danger`) para mostrar/ocultar títulos com status `PROTESTADO` (cor `danger`).
- **Atrasados**: Cards com status `ATRASADO` assumem cor `warning` para destaque visual.
- **Auto-Ativação**: Ao selecionar explicitamente "DEVOLUCAO" ou "PROTESTADO" no filtro superior do Kanban, o sistema ativa automaticamente o switch correspondente na coluna.

### Sub-Dashboards Departamentais:
- **Visão Geral**: Consolidação macro dos KPIs de Financeiro, Logística e Comercial.
- **Financeiro**: Sub-abas `Gerencial` e `Gerente/Representante`, contendo o painel `Atual` (data de hoje, cards de Total Vencido, Total Protestado e evolução vs ontem) e a grid principal de títulos.
- **Logística**: Ocorrências sem data de entrega e de devolução.
- **Comercial**: Acordos comerciais e ranking dos 5 maiores acordos.
- **Modais Integrados**: Modal de Tratativas e Modal de Histórico de Pendências.
