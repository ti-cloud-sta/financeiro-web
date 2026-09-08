# CONTEXTO TÉCNICO — Módulos: Despesas de Viagens & Plano de Saúde

> **ATENÇÃO AO AGENTE:** Este documento é uma fonte de verdade. Antes de qualquer ação de desenvolvimento nos módulos abaixo, leia-o inteiro. Se você sentir que está deduzindo algo que não está documentado aqui, **pare e pergunte ao usuário**. Não invente, não assuma, não extrapole.

---

## PARTE 1 — MÓDULO DESPESAS DE VIAGENS

### 1.1 Localização dos Arquivos

**Frontend:**
```
frontend/src/app/pages/despesas-viagens/
  despesas-viagens.component.ts       (1591 linhas — toda a lógica)
  despesas-viagens.component.html     (1539 linhas — template)
  despesas-viagens.component.scss     (1552 linhas — estilos)
```

**Frontend — Serviços utilizados:**
```
frontend/src/app/core/services/
  importacoes.service.ts     ← principal, chama todos os endpoints do módulo
  colaboradores.service.ts
  categorias.service.ts
  empresas.service.ts
  centros-custo.service.ts
  unidades.service.ts
  theme.service.ts            ← Signal do tema claro/escuro (reativo via effect())
```

**Backend:**
```
backend/app/routers/
  importacoes.py              (3540 linhas — router principal do módulo + inadimplência + plano saúde)

backend/app/services/
  ia_service.py               (1617 linhas — integração Gemini API + todos os parsers)
  dashboard_service.py        (646 linhas — lógica analítica em memória)
  movimentacao_service.py     (64 linhas — persistência de importações e movimentações)
  importacao_service.py       (39 linhas — listagem paginada e exclusão)

backend/app/models/
  movimentacao.py             ← tabela central de cada despesa
  importacao.py               ← tabela de lotes de importação

backend/app/repositories/
  importacao_repository.py    ← CRUD de importações com joinedload
  colaborador_repository.py   ← busca por nome, CPF, nome normalizado
  categoria_repository.py     ← busca por nome exato (case-sensitive!)
  empresa_repository.py       ← busca por nome exato (case-sensitive!)

backend/app/schemas/
  movimentacao.py             ← DespesaIAPayload + SalvarImportacaoIAPayload
```

---

### 1.2 Endpoints da API (Despesas de Viagens)

| Método | URL | Função |
|--------|-----|--------|
| `GET` | `/api/v1/importacoes/` | Lista importações paginada. Filtro `categoria=IA_DESPESAS` |
| `POST` | `/api/v1/importacoes/ia/analise-extrato` | Envia arquivo para análise via Gemini. FormData: `file` + `empresa_nome` |
| `POST` | `/api/v1/importacoes/ia/salvar` | Persiste importação + movimentações. Body: `SalvarImportacaoIAPayload` |
| `DELETE` | `/api/v1/importacoes/{id}` | Deleta importação com cascade em movimentacoes |
| `GET` | `/api/v1/importacoes/dashboard` | Dashboard Visão Geral + Categorias |
| `GET` | `/api/v1/importacoes/dashboard/analitico` | Dashboard Comercial/Marketing + Relatório |

---

### 1.3 Modelo de Dados

**Tabela `movimentacoes`:**
```
idMovimentacoes  Integer PK
idCategoria      FK → categorias.idCategorias
idColaborador    FK → colaboradores.idColaborador
idEmpresa        FK → empresas.idEmpresas
idImportacoes    FK → importacoes.idImportacoes
valor            Float(18,2)
createdAt        DateTime  ← ATENÇÃO: usada como "data da despesa" — é a data de importação!
```

> ⚠️ **PROBLEMA CONHECIDO:** Não existe campo `data_despesa` separado. `createdAt` reflete
> quando o registro foi inserido no banco (data da importação), não a data real da despesa
> no extrato. Isso distorce filtros de período. Quando implementar a solução Python, incluir
> campo `data_despesa` como parte do plano.

**Tabela `importacoes`:**
```
idImportacoes    Integer PK
nomeArquivo      String(200)
extensaoArquivo  String(10)
idEmpresa        FK → empresas (nullable)
tipo             String(45)  ← "IA_DESPESAS" para este módulo
idUserInc        FK → users (nullable)
createdAt        DateTime    ← data de importação
```

---

### 1.4 Fluxo Atual de Importação (FLUXO QUE SERÁ SUBSTITUÍDO)

```
1. Usuário seleciona empresa → clica "Importar" → abre modal
2. Seleciona arquivo (PDF/XLS/CSV/DOC) → clica "Processar"
3. Frontend: POST /ia/analise-extrato (FormData: file + empresa_nome)
4. Backend (importacoes.py L42-111):
   a. Busca todas categorias do banco (limit=1000)
   b. Busca todos colaboradores do banco (limit=5000)
   c. Chama IAService.analisar_extrato() → envia TUDO direto ao Gemini
   d. Gemini retorna JSON estruturado (DespesaExtraida: empresa, colaborador, categoria, valor)
   e. Consolida por chave "colaborador|categoria" (soma valores duplicados)
   f. Retorna {sucesso: true, dados: [...]}
5. Frontend exibe tabela editável (ng-select colaborador/categoria, input valor)
6. Usuário confirma → POST /ia/salvar
7. MovimentacaoService.salvar_importacao_ia():
   a. Cria importacao (tipo="IA_DESPESAS")
   b. Para cada despesa: busca categoria, colaborador, empresa por NOME EXATO
   c. Se qualquer nome não encontrado → HTTP 400 (bug crítico)
   d. Cria Movimentacao para cada despesa
   e. db.commit()
```

> ⚠️ **PROBLEMA CRÍTICO ATUAL:** `get_by_nome` de categoria, colaborador e empresa usa
> comparação de string **exata e case-sensitive** (`Colaborador.nome == nome`). Se o Gemini
> retornar "joão silva" em vez de "JOÃO SILVA", o salvar falha com HTTP 400.

---

### 1.5 Bugs e Pendências Identificados

| # | Problema | Localização | Impacto |
|---|---|---|---|
| 1 | `alert()` nativo em `reprocessarImportacao()` | `.ts` L534 | Viola AGENTS.md |
| 2 | `alert()` nativo em `exportRelatorioToExcel()` | `.ts` L1317 | Viola AGENTS.md |
| 3 | `alert()` nativo em `exportToPDF()` | `.ts` L1585 | Viola AGENTS.md |
| 4 | `reprocessarImportacao()` não implementada | `.ts` L534 | Botão existe mas não faz nada |
| 5 | Filtro CC na aba Comercial/Marketing é local (frontend) | `.ts` | Não passa para o backend |
| 6 | Filtro CC na aba Relatório é local (frontend) | `.ts` | Não passa para o backend |
| 7 | `createdAt` = data de importação, não da despesa | `movimentacao.py` | Filtros de período errados |
| 8 | `isDashboardLoading` compartilhado entre Visão Geral e Categorias | `.ts` | Loading de uma afeta a outra |

---

### 1.6 Estrutura Visual do Frontend

```
.page-container (padding: 0 — edge-to-edge)
└── .main-layout
    ├── aside.main-sidebar          ← colapsável, persiste em localStorage('sidebarCollapsed')
    │   ├── item: Dashboard
    │   └── item: Atualização de Dados
    └── main.main-content
        ├── sidebarTab = 'dashboard'
        │   ├── .config-nav (4 abas)
        │   │   ├── 'visao-geral'          → 4 KPIs + Área Chart + 2 Donuts + Mapa + Top5
        │   │   ├── 'categorias'           → 2 KPIs + Donut + lista + Top Spenders
        │   │   ├── 'comercial-marketing'  → 7 gráficos + Rankings + Butterfly + Matriz
        │   │   └── 'relatorio'            → Filtros + Tabela Matriz exportável Excel
        │   └── Filtros de período (3 conjuntos independentes por aba)
        └── sidebarTab = 'atualizacao'
            ├── Grid de cards das empresas (dinâmico, da API)
            │   └── Ícone baseado no nome (hardcoded: kinto→carro, onfly→avião etc.)
            ├── Modal de importação
            │   ├── Estado 'idle'       → dropzone + botão processar
            │   ├── Estado 'processing' → animação 4 steps
            │   └── Estado 'done'       → tabela editável (ng-select + input)
            └── Histórico de importações (grid paginada, busca, excluir)
```

---

### 1.7 Inventário de Gráficos ECharts

| Variável TS | Tipo ECharts | Aba |
|---|---|---|
| `chartOptionArea` | Line stacked area | Visão Geral |
| `chartOptionDonutCategoria` | Pie/Donut | Visão Geral |
| `chartOptionDonutEmpresa` | Pie/Donut | Visão Geral |
| `chartOptionMapa` | Map brazil | Visão Geral |
| `chartOptionAreaCategorias` | Line stacked area | Categorias |
| `chartOptionDonutCategoriaTab` | Pie/Donut | Categorias |
| `categoryEmpresasOption` | Bar horizontal | Categorias (detalhe) |
| `chartAnaliticoBarrasVerticais` | Bar vertical | Comercial/Marketing |
| `chartAnaliticoCategoriaBarras` | Bar horizontal | Comercial/Marketing |
| `chartAnaliticoCategoriaDonut` | Pie/Donut | Comercial/Marketing |
| `chartAnaliticoButterfly` | Bar dual horizontal | Comercial/Marketing |
| `chartAnaliticoEvolucaoLinha` | Line smooth | Comercial/Marketing |
| `chartAnaliticoCentroCusto` | Bar horizontal | Comercial/Marketing |
| `chartAnaliticoMapa` | Map brazil | Comercial/Marketing |

**Mapa:** arquivo estático `/assets/maps/brazil.json`. Registrado via `echarts.registerMap('brazil', geoJson)`.
**Tema:** `ThemeService.activeTheme()` é Signal. Um `effect()` no constructor recria todos os gráficos ao mudar o tema.

---

### 1.8 DashboardService — Lógica de Agregação

O `DashboardService` **não usa GROUP BY no SQL**. Carrega as movimentações filtradas em memória e faz todas as agregações em Python:

- Filtros aplicados via SQL: `data_inicio`, `data_fim`, `id_empresa`, `id_colaborador`, `id_categoria`, `tipo_importacao`
- Agregações em Python: totais por mês, por categoria, por empresa, por centro de custo, por estado, por colaborador, butterfly (campo `papel` do colaborador: "COMERCIAL" ou "MARKETING"), ranking, matriz colaborador × categoria
- Limitação: `detalhes` retorna no máximo 200 movimentações

---

## PARTE 2 — MÓDULO PLANO DE SAÚDE

### 2.1 Localização dos Arquivos

**Backend:**
```
backend/app/routers/
  plano_saude.py           (96 linhas — relatórios, exportações, conciliação)
  plano_saude_ia.py        (119 linhas — análise/confirmação de PDFs)

backend/app/services/
  plano_saude_ia_service.py  (623 linhas — orquestra extração + resolução de colaboradores + persistência)
  plano_saude_service.py     (470 linhas — relatório geral, exportação Excel, contabilidade CSV/TXT, conciliação)
  ia_service.py              (1617 linhas — todos os parsers determinísticos + fallback IA)

backend/app/repositories/
  colaborador_alias_repository.py  ← sistema de aprendizado de nomes divergentes
  colaborador_repository.py        ← get_by_documento, get_by_nome, get_by_nome_normalizado

backend/app/models/
  colaborador_alias.py     ← tabela colaborador_aliases (memória de nomes aprendidos)

backend/app/schemas/
  plano_saude.py           ← Payloads de confirmação (Sorriso e Unimed Odonto) e exportação
```

---

### 2.2 Endpoints da API (Plano de Saúde)

| Método | URL | Função |
|--------|-----|--------|
| `GET` | `/api/v1/plano-saude/relatorio-geral` | Relatório paginado por mês/ano |
| `GET` | `/api/v1/plano-saude/relatorio-geral/exportar` | Download Excel do relatório |
| `GET` | `/api/v1/plano-saude/relatorio-geral/contabilidade` | Download CSV contabilidade |
| `GET` | `/api/v1/plano-saude/relatorio-geral/contabilidade-txt` | Download TXT largura fixa |
| `POST` | `/api/v1/plano-saude/relatorio-geral/conciliar` | Conciliação planilha vs sistema |
| `POST` | `/api/v1/importacoes/plano-saude/universal/analisar` | **Parser Python (regex) — rota principal** |
| `POST` | `/api/v1/importacoes/plano-saude/sorriso/analisar` | **Parser IA (Gemini) — Sorriso Odontológico** |
| `POST` | `/api/v1/importacoes/plano-saude/sorriso/confirmar` | Persiste importação Sorriso |
| `POST` | `/api/v1/importacoes/plano-saude/sorriso/exportar` | Exporta Excel de conferência Sorriso |
| `POST` | `/api/v1/importacoes/plano-saude/unimed-odonto/analisar` | **Parser Python (regex) — Unimed Odonto** |
| `POST` | `/api/v1/importacoes/plano-saude/unimed-odonto/confirmar` | Persiste importação Unimed Odonto |
| `POST` | `/api/v1/importacoes/plano-saude/unimed-odonto/exportar` | Exporta Excel de conferência Unimed |

> **Nota de arquitetura:** As rotas `/importacoes/plano-saude/...` vivem no arquivo
> `routers/plano_saude_ia.py` mas são montadas DENTRO do router de importações em
> `importacoes.py` linha 27: `router.include_router(plano_saude_ia_router, prefix="/plano-saude")`

---

### 2.3 O Coração: Parsers Determinísticos em Cascata

O método `extrair_beneficiarios_pdf_universal()` no `IAService` tenta **8 parsers em sequência**.
O primeiro que produzir resultado é usado. Nenhuma chamada à IA é feita nesse ponto.

```python
formatos = [
    lambda: self._fmt_unimed_single_line(lines),       # Formato A
    lambda: self._fmt_matricula_suffix(lines),          # Formato E
    lambda: self._fmt_seguro_vida(lines),               # Formato B
    lambda: self._fmt_rubrica_multiline(page_texts),    # Formato A2
    lambda: self._fmt_coparticipacao(lines),            # Formato H
    lambda: self._fmt_responsavel(lines),               # Formato G
    lambda: self._fmt_sorriso_fragmented(lines),        # Formato F
    lambda: self._fmt_generic(lines),                   # Formato C (genérico)
]
```

#### Detalhe de cada parser:

**`_fmt_unimed_single_line` (Formato A):**
- Detecta: padrão de número de beneficiário `X.XXXXXXX.XXXXXXXX-X` (pelo menos 5 ocorrências)
- Cada linha contém: nome, matrícula, tipo `T/D/A`, valor, e eventualmente CPF
- CPF tentado em dois formatos: `000.000.000-00` (formatado) ou 8-11 dígitos consecutivos (sem pontuação)
- Agrupa por matrícula (prefix)

**`_fmt_matricula_suffix` (Formato E — Analítico de Taxa Unimed):**
- Detecta: linhas no padrão `prefixo.partes-sufixo NOME TIPO RUBRICA valor`
- Sufixo `00` = titular, demais sufixos = dependentes da mesma família
- **Nunca tem CPF** → marcado como `permite_fallback_nome = True`

**`_fmt_seguro_vida` (Formato B):**
- Detecta: marcadores `ALT/INC/EXC` colados a dígitos nas linhas (pelo menos 5)
- Padrão: `valor + matrícula + nome + tipo (T/D) + CPF`
- Se campo após T/D tem 10-11 dígitos, é o CPF

**`_fmt_rubrica_multiline` (Formato A2 — Demonstrativo Analítico Unimed):**
- Detecta: rubricas específicas (Mensalidade, Prêmio, Cobrança/Devolução Retroativa)
- Registro de beneficiário quebrado em múltiplas linhas
- Janela de busca: 200 chars antes da rubrica para encontrar nome + CPF

**`_fmt_coparticipacao` (Formato H — Co-participação / Analítico de Serviço):**
- Detecta: headers `NOME - MATRÍCULA + Matrícula` + linhas `TOTAL TITULAR`
- Usa o total já calculado no PDF, não soma individual por atendimento
- **Nunca tem CPF** → marcado como `permite_fallback_nome = True`

**`_fmt_responsavel` (Formato G):**
- Detecta: blocos `Responsavel: <cod>` + linhas `codigo NOME ... Valor Benef: valor`
- Titular identificado pelo código que bate com o `Responsavel:`
- Ordem dentro do bloco não é confiável (titular pode vir depois do dependente)

**`_fmt_sorriso_fragmented` (Formato F — Sorriso Odontológico via PyPDF):**
- Detecta: tipo `T` ou `D` isolado em sua própria linha (pelo menos 5 ocorrências)
- O PyPDF fragmenta as tabelas do Sorriso em uma célula por linha
- Nome: busca para trás a partir do índice do tipo; Valor: busca para frente
- CPF: busca sequência de 8-11 dígitos para frente

**`_fmt_generic` (Formato C — Genérico):**
- Detecta: padrão `NOME ... valor ... T/D` ou `valor ... NOME ... T/D` em uma linha
- Último recurso; menos preciso
- Skip de palavras reservadas: SUBTOTAL, TOTAL GERAL, PÁGINA, COMPETÊNCIA etc.

---

### 2.4 Fallback para IA (Gemini) — Quando e Como

A IA é acionada **somente** em duas condições, após todos os parsers Python rodarem:

```python
# Condição 1: Nenhum beneficiário extraído (PDF escaneado, layout completamente desconhecido)
if not titulares_list:
    motivo_fallback = "nenhum beneficiário extraído"

# Condição 2: Total calculado ≠ total impresso no documento (diferença > 1% ou R$ 1,00)
elif total_esperado is not None and abs(soma_calculada - total_esperado) > max(1.0, total_esperado * 0.01):
    motivo_fallback = f"calculado={soma_calculada} vs impresso={total_esperado}"
```

O total impresso é detectado por `_detectar_total_esperado()` que procura âncoras:
- `TOT AL EMPRESA`, `TOTAL GERAL`, `TOTAL DA FATURA`, `VALOR TOTAL:`, `^Total.:`

Se a IA também falhar → resultado do Python é usado mesmo assim (melhor que nada).

---

### 2.5 Parser de Planilha (CSV/Excel) — `extrair_beneficiarios_planilha()`

Para arquivos `.csv`, `.xlsx`, `.xls`, um parser separado é usado (sem regex de texto):

**Layout de colunas fixas esperado:**
- Coluna B (índice 1) = Código do Titular (agrupa família)
- Coluna C (índice 2) = Tipo: `T` (titular) ou `D` (dependente)
- Coluna J (índice 9) = Valor da mensalidade
- Coluna P (índice 15) = CPF do titular do grupo (mesmo em todas as linhas T/D)

Headers buscados dinamicamente: `nome beneficiário`, `nome titular` (busca case-insensitive por `_find_col()`).

---

### 2.6 Resolução de Colaboradores — `_resolver_colaborador()`

Hierarquia rígida, sem ambiguidade:

```
1. CPF presente no PDF:
   → ColaboradorRepository.get_by_documento(cpf_normalizado_11_digitos)
   → Se encontrado: usa. Se não encontrado: FICA SEM VÍNCULO (não cai para nome!)

2. CPF ausente → consulta tabela de aliases:
   → ColaboradorAliasRepository.get_by_nome_divergente(nome_pdf)
   → Se existe alias: usa o colaborador vinculado

3. CPF ausente + formato sem CPF (unimed_matricula_sufixo ou coparticipacao):
   → permite_fallback_nome = True
   → ColaboradorRepository.get_by_nome_normalizado(nome_pdf)
   → Normalização: maiúsculas, remove acentos, sem espaço duplo — comparação EXATA

4. Nenhum match: retorna None → usuário associa manualmente na tela de conferência
```

**Normalização de CPF (`_normaliza_cpf`):**
- Remove todos os não-dígitos
- Se resultado tem 8-11 dígitos: completa com zeros à esquerda até 11
- CPFs abaixo de 8 dígitos: descartados (inválidos)
- Razão: alguns PDFs guardam CPF como número, perdendo zeros iniciais

---

### 2.7 Sistema de Aprendizado — Alias

Tabela `colaborador_aliases`:
```
idAlias          Integer PK
idColaborador    FK → colaboradores.idColaborador
nome_divergente  String(120) UNIQUE  ← nome como aparece no PDF
createdAt        DateTime
```

**Como funciona:**
- Na confirmação (`confirmar_sorriso` / `confirmar_unimed_odonto`), se `nome_pdf != colaborador.nome`:
  → `alias_repo.create_or_update(colab.idColaborador, nome_pdf.strip())` é chamado
- Na próxima importação com o mesmo `nome_pdf`:
  → `alias_repo.get_by_nome_divergente(nome_pdf)` retorna o vínculo diretamente
  → Sem precisar de IA, sem interação manual

---

### 2.8 Persistência na Confirmação (`confirmar_sorriso` / `confirmar_unimed_odonto`)

Fluxo idêntico nas duas rotas:

```python
1. _resolver_empresa_e_categoria(id_empresa):
   - Tenta empresa pelo ID
   - Fallback: empresa de nome "RDV - SANTA MARIA"
   - Fallback: primeira empresa do banco
   - Categoria: se "seguro" no nome da empresa → "Seguro/Saúde" (id=9)
              se não → "Plano de Saúde" (id=8)

2. Cria Importacao(tipo="PLANO_SAUDE" ou "SEGURO")
   db.flush() → gera idImportacoes antes do commit

3. Para cada titular:
   a. Resolve colaborador: primeiro por id_db (manual), depois por CPF normalizado
   b. Se não encontrado → adiciona em erros_colaboradores, continua (não cancela tudo!)
   c. Salva alias se nome_pdf != colaborador.nome
   d. Atualiza Centro de Custo do colaborador se foi modificado na tela
   e. (Apenas Unimed) Atualiza Unidade do colaborador se foi modificada na tela
   f. Cria Movimentacao(valor = titular.valor_total)
   g. Se payload.dataCompetencia: createdAt = datetime.strptime(dataCompetencia, "%Y-%m-%d")
      → DIFERENÇA CRÍTICA vs Despesas: aqui a data é a competência real, não a de importação!

4. db.commit()
5. Retorna {sucesso, idImportacoes, movimentacoes_criadas, erros_colaboradores}
```

> ⚠️ **ATENÇÃO:** Colaboradores não encontrados são **ignorados silenciosamente** (com log
> no console). A importação prossegue parcialmente. Isso é intencional — diferente de
> Despesas que lança HTTP 400 e cancela tudo.

---

### 2.9 Diferenças Críticas: Sorriso vs Universal vs Unimed

| Aspecto | `/universal/analisar` | `/sorriso/analisar` | `/unimed-odonto/analisar` |
|---|---|---|---|
| **Estratégia** | Python → IA se falhar | **Sempre IA (Gemini)** | Python puro |
| **Parsing** | 8 parsers em cascata | PyPDF → texto → Gemini | Regex específico de matrícula |
| **CPF** | Tenta extrair | Gemini extrai | Regex na linha |
| **Fallback nome** | Para formatos sem CPF | Não (tem CPF via Gemini) | `difflib.get_close_matches(cutoff=0.85)` |

> ⚠️ **NOTA SOBRE SORRISO:** A rota `/sorriso/analisar` sempre chama o Gemini.
> O Formato F (`_fmt_sorriso_fragmented`) no parser universal já cobre PDFs do Sorriso
> via Python puro. A rota Sorriso legada existe por razões históricas.

---

## PARTE 3 — MÓDULO DESPESAS DE VIAGENS: PARSERS IMPLEMENTADOS

### 3.1 O Problema Resolvido

Anteriormente, todo arquivo enviado ia direto para o Fallback Genérico do Gemini, gerando lentidão, custos desnecessários e falhas de mapeamento. O sistema foi refatorado criando o serviço especializado `despesas_viagens_parser_service.py`, que agora atua como uma esteira de identificação e extração de dados.

### 3.2 O Modelo Implementado (Despesas de Viagens)

O fluxo principal foi alterado para roteamento dinâmico:
```
Arquivo → analisar_arquivo() (DespesasViagensParserService)
   ├── É Kinto? → Parser Python
   ├── É Localiza? → Parser Python
   ├── É Onfly? → Parser Python
   ├── É RDV Santa Maria? → Extrator IA Específico (Gemini + Prompts otimizados)
   ├── É DANFE Rosemary? → Extrator IA Específico
   ├── É Fatura Cartão PJ Eduardo? → Extrator IA Específico
   ├── É Fatura Agência Tastur? → Extrator IA Específico
   ├── É Fatura Maiorca? → Extrator IA Específico
   ├── É Pedágio Sem Parar? → Extrator IA Específico (Com mapeamento de placas para colaboradores)
   └── Se não for nenhum dos acima → Fallback IA Genérico
```

### 3.3 Parsers Disponíveis (`despesas_viagens_parser_service.py`)

**Parsers Determinísticos (Python):**
- `_parse_kinto_pdf`
- `_parse_localiza_pdf`
- `_parse_localiza_rent_pdf`
- `_parse_onfly_fatura_pdf`
- `_parse_onfly_pdf`

**Parsers Especializados Híbridos (Gemini API com regras engessadas):**
- `_parse_santamaria_rdv_via_ia`
- `_parse_danfe_rosemary_via_ia`
- `_parse_fatura_cartao_eduardo_via_ia`
- `_parse_tastur_fatura_via_ia`
- `_parse_maiorca_fatura_via_ia`
- `_parse_semparar_fatura_via_ia`

### 3.4 Mecânica de Mapeamento (Banco de Dados)

Após a extração pelo parser (seja Python ou IA), o `despesas_viagens_parser_service.py` executa o mesmo loop de normalização que o Módulo de Plano de Saúde:
- Valida a **Categoria** via nome exato ou tabela `CategoriaAlias`.
- Valida o **Colaborador** (removendo acentos e capitalização) via nome ou `ColaboradorAliasRepository`.
- Se o campo não for encontrado, ele adiciona a flag `_encontrada = False` permitindo a correção amigável pelo usuário diretamente na tela de importação no Frontend.

---

## PARTE 4 — REGRAS DE OURO PARA O AGENTE

> Estas regras previnem erros comuns ao trabalhar nestes módulos.

1. **NUNCA usar `.alert()` ou `.confirm()` no frontend.** Use sempre `<app-confirm-modal>`.

2. **Componentes shared disponíveis** (checar antes de criar novos):
   `avatar`, `badge`, `breadcrumb`, `button`, `card`, `dropdown`, `empty-state`,
   `error-state`, `input`, `loading`, `modal`, `skeleton`, `tooltip`

3. **O router `importacoes.py` tem 3540 linhas** e contém múltiplos módulos.
   Ao editar, localize exatamente a seção de Despesas de Viagens (linhas 42-291).
   Não confunda com as rotas de inadimplência (L130+) ou extratores atacadão/Sendas (L387+).

4. **`idEmpresa` da Importacao** vem da primeira despesa da lista no `salvar_importacao_ia()`.
   Se o arquivo tiver despesas de múltiplas empresas, isso pode estar errado.

5. **A rota universal `/plano-saude/universal/analisar`** é a principal. Ela está montada
   dentro do router `importacoes.py` via `include_router` na linha 27.

6. **O campo `papel` do Colaborador** (valores: "COMERCIAL" ou "MARKETING") é usado pelo
   Butterfly Chart na aba Comercial/Marketing. Colaboradores sem `papel` preenchido
   ficam invisíveis no gráfico.

7. **Filtros de Centro de Custo** nas abas Comercial/Marketing e Relatório são **locais**
   (frontend filtra `detalhesMatrizOriginal`). Não são enviados ao backend.

8. **O mapa do Brasil** carrega de `/assets/maps/brazil.json`. Se falhar, nenhum erro
   aparece ao usuário — apenas o gráfico fica vazio.

9. **Ao adicionar novos campos** à tabela `movimentacoes`, sempre verificar se
   `DashboardService` precisa ser atualizado para incluir o campo nas queries.

10. **O Gemini** é chamado via `google-genai` SDK com `client.aio.models.generate_content()`.
    Sempre usar `response_mime_type="application/json"` + `response_schema=...` para saída
    estruturada. O retry padrão é 3 tentativas com backoff (429 → 5s, 503/500 → 2s × attempt).

---

## PARTE 5 — REFERÊNCIA RÁPIDA DE ARQUIVOS

### Onde gerenciar os parsers de despesas:
- **Serviço Principal:** `backend/app/services/despesas_viagens_parser_service.py` (contém a orquestração, fallback genérico, parsers determinísticos e parsers de IA por fornecedor)
- **Router:** As rotas chamam diretamente o parser no arquivo `backend/app/routers/importacoes.py`

### Onde está cada coisa:
```
Lógica de extração IA atual de despesas:    ia_service.py → analisar_extrato() (L1062)
Parsers Python do plano de saúde:           ia_service.py → _fmt_*() (L163-614)
Parser universal (orquestrador):            ia_service.py → extrair_beneficiarios_pdf_universal() (L698)
Fallback IA do universal:                   ia_service.py → _extrair_beneficiarios_via_ia_fallback() (L616)
Parser de planilha:                         ia_service.py → extrair_beneficiarios_planilha() (L808)
Endpoint de análise de despesas (atual):    importacoes.py L42
Endpoint de salvar despesas:                importacoes.py L116
Serviço de persistência de despesas:        movimentacao_service.py L17
Serviço de análise do plano de saúde:       plano_saude_ia_service.py L184
Resolução de colaboradores (plano saúde):   plano_saude_ia_service.py L53
Aprendizado de aliases:                     colaborador_alias_repository.py L13
```
