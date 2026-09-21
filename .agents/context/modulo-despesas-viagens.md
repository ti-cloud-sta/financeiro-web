# Contexto de Negócio e Técnico: Módulo de Despesas de Viagens

Documentação técnica completa, regras de negócio, esteira de parsers e arquitetura do módulo de Despesas de Viagens corporativas.

---

## 1. Localização dos Arquivos

### Frontend
- `frontend/src/app/pages/despesas-viagens/`
  - `despesas-viagens.component.ts`: Toda a lógica, Signals de estado, chamadas de serviço e handlers de ECharts.
  - `despesas-viagens.component.html`: Template com abas (`visao-geral`, `categorias`, `comercial-marketing`, `relatorio`, `atualizacao`), modal de importação e filtros.
  - `despesas-viagens.component.scss`: Estilos no padrão SaaS, layout edge-to-edge (`padding: 0;`).

### Serviços Frontend Utilizados
- `frontend/src/app/core/services/`
  - `importacoes.service.ts`: Serviço principal que invoca os endpoints do módulo.
  - `colaboradores.service.ts`, `categorias.service.ts`, `empresas.service.ts`, `centros-custo.service.ts`, `unidades.service.ts`.
  - `theme.service.ts`: Signal reativo do tema claro/escuro (`activeTheme()`) monitorado por `effect()` no constructor para redesenhar gráficos ECharts.

### Backend
- `backend/app/routers/`
  - `importacoes.py`: Router principal contendo endpoints de importação, dashboards e deleção.
- `backend/app/services/`
  - `despesas_viagens_parser_service.py`: Esteira de parsers determinísticos e especializados por fornecedor.
  - `ia_service.py`: Integração com Gemini API (`google-genai`) e fallback genérico.
  - `dashboard_service.py`: Lógica analítica e agregações em memória.
  - `movimentacao_service.py`: Persistência de importações e movimentações.
  - `importacao_service.py`: Listagem paginada e exclusão.
- `backend/app/models/`
  - `movimentacao.py`: Tabela central `movimentacoes`.
  - `importacao.py`: Lotes de importação (`tipo = 'IA_DESPESAS'`).
- `backend/app/repositories/`
  - `importacao_repository.py`, `colaborador_repository.py`, `categoria_repository.py`, `empresa_repository.py`.

---

## 2. Endpoints da API

| Método | URL | Função |
|---|---|---|
| `GET` | `/api/v1/importacoes/` | Lista importações paginadas (filtro `categoria=IA_DESPESAS`). |
| `POST` | `/api/v1/importacoes/ia/analise-extrato` | Envia arquivo para esteira de análise (FormData: `file` + `empresa_nome`). |
| `POST` | `/api/v1/importacoes/ia/salvar` | Persiste lote de importação e movimentações validadas. |
| `DELETE` | `/api/v1/importacoes/{id}` | Deleta importação com exclusão em cascata nas movimentações. |
| `GET` | `/api/v1/importacoes/dashboard` | Dados agregados para abas Visão Geral e Categorias. |
| `GET` | `/api/v1/importacoes/dashboard/analitico` | Dados agregados para aba Comercial/Marketing e Relatório Matriz. |

---

## 3. Modelo de Dados e Peculiaridades

### Tabela `movimentacoes`:
- `idMovimentacoes` (PK)
- `idCategoria` (FK → `categorias`)
- `idColaborador` (FK → `colaboradores`)
- `idEmpresa` (FK → `empresas`)
- `idImportacoes` (FK → `importacoes`)
- `valor` (Float 18,2)
- `createdAt` (DateTime): Utilizada historicamente como "data da despesa" (refletindo a data da importação).

### Tabela `importacoes`:
- `idImportacoes` (PK), `nomeArquivo`, `extensaoArquivo`, `idEmpresa`, `tipo` ("IA_DESPESAS"), `idUserInc`, `createdAt`.

---

## 4. Esteira de Parsers (`despesas_viagens_parser_service.py`)
Arquivos enviados passam por identificação automática de fornecedor antes de qualquer chamada externa:

```text
Arquivo → analisar_arquivo() (DespesasViagensParserService)
   ├── É Kinto? → Parser Python Determinístico (_parse_kinto_pdf)
   ├── É Localiza? → Parser Python Determinístico (_parse_localiza_pdf / _parse_localiza_rent_pdf)
   ├── É Onfly? → Parser Python Determinístico (_parse_onfly_fatura_pdf / _parse_onfly_pdf)
   ├── É RDV Santa Maria? → Extrator IA Específico (Gemini + Prompt otimizado)
   ├── É DANFE Rosemary? → Extrator IA Específico
   ├── É Fatura Cartão PJ Eduardo? → Extrator IA Específico
   ├── É Fatura Tastur? → Extrator IA Específico
   ├── É Fatura Maiorca? → Extrator IA Específico
   ├── É Pedágio Sem Parar? → Extrator IA Específico (Mapeamento de placas para colaboradores)
   └── Outros/Desconhecidos → Fallback IA Genérico
```

### Normalização de Entidades:
- Validação de Categoria: via nome exato ou tabela `categoria_alias`.
- Validação de Colaborador: remoção de acentos e case via `colaborador_repository` ou `colaboradoralias`.
- Itens não encontrados recebem flag `_encontrada = False`, permitindo correção direta na tabela editável do frontend antes de salvar.

---

## 5. Estrutura Visual e Inventário de Gráficos ECharts

### Navegação do Módulo:
- Sidebar: Aba `Dashboard` e Aba `Atualização de Dados`.
- Abas de Dashboard (`.config-nav`):
  1. `visao-geral`: 4 KPIs + Área Chart + 2 Donut Charts + Mapa do Brasil + Top 5.
  2. `categorias`: 2 KPIs + Donut + Lista de categorias + Top Spenders.
  3. `comercial-marketing`: 7 gráficos analíticos + Rankings + Butterfly Chart + Matriz.
  4. `relatorio`: Painel de filtros + Tabela Matriz exportável para Excel.

### Gráficos ECharts Utilizados:
- `chartOptionArea`: Linha empilhada de evolução temporal.
- `chartOptionDonutCategoria` & `chartOptionDonutEmpresa`: Distribuição por categoria e empresa.
- `chartOptionMapa`: Mapa coroplético do Brasil (carrega `/assets/maps/brazil.json`).
- `chartAnaliticoButterfly`: Gráfico dual horizontal comparando perfil COMERCIAL vs MARKETING (usa o campo `papel` do colaborador).
- `chartAnaliticoBarrasVerticais`, `chartAnaliticoCategoriaBarras`, `chartAnaliticoCentroCusto`, `chartAnaliticoEvolucaoLinha`.

---

## 6. Regras de Ouro do Módulo
1. **Sem alerts nativos**: Proibido `alert()` e `confirm()`. Usar `<app-confirm-modal>`.
2. **Filtro de Papel (Butterfly)**: Colaboradores sem `papel` definido ("COMERCIAL" ou "MARKETING") ficam invisíveis no Butterfly Chart.
3. **Filtros Locais de Centro de Custo**: Nas abas Comercial/Marketing e Relatório, o filtro de Centro de Custo filtra localmente o dataset `detalhesMatrizOriginal` no frontend.
4. **Chamadas Gemini API**: Feitas via `google-genai` SDK com `response_mime_type="application/json"` e `response_schema` estruturado, com 3 retries e backoff exponencial.
