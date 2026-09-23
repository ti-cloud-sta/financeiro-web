# Contexto de Negócio e Técnico: Módulo de Plano de Saúde

Documentação técnica completa, regras de negócio, parsers em cascata e aprendizado contínuo de beneficiários.

---

## 1. Localização dos Arquivos

### Backend
- `backend/app/routers/`
  - `plano_saude.py`: Relatórios gerais, exportações Excel/CSV/TXT e conciliação financeira.
  - `plano_saude_ia.py`: Endpoints de análise e confirmação de PDFs (montado dentro de `importacoes.py` no prefixo `/plano-saude`).
- `backend/app/services/`
  - `plano_saude_ia_service.py`: Orquestra extração, resolução de colaboradores e persistência de lotes.
  - `plano_saude_service.py`: Relatórios gerenciais, layouts contábeis (CSV/TXT) e conciliação.
  - `ia_service.py`: Contém todos os parsers determinísticos e o fallback para Gemini API.
- `backend/app/repositories/`
  - `colaborador_alias_repository.py`: Sistema de aprendizado contínuo de nomes divergentes (`ColaboradorAlias`).
  - `colaborador_repository.py`: Buscas por documento (CPF), nome exato e nome normalizado.
- `backend/app/models/`
  - `colaborador_alias.py`: Entidade `colaborador_aliases`.
- `backend/app/schemas/`
  - `plano_saude.py`: Payloads de confirmação (Sorriso Odonto, Unimed Odonto) e exportações.

---

## 2. Endpoints da API

| Método | URL | Função |
|---|---|---|
| `GET` | `/api/v1/plano-saude/relatorio-geral` | Relatório paginado por competência (mês/ano). |
| `GET` | `/api/v1/plano-saude/relatorio-geral/exportar` | Download de relatório em planilha Excel. |
| `GET` | `/api/v1/plano-saude/relatorio-geral/contabilidade` | Exportação contábil em formato CSV. |
| `GET` | `/api/v1/plano-saude/relatorio-geral/contabilidade-txt` | Exportação contábil em TXT de largura fixa. |
| `POST` | `/api/v1/plano-saude/relatorio-geral/conciliar` | Conciliação entre planilha e base do sistema. |
| `POST` | `/api/v1/importacoes/plano-saude/universal/analisar` | **Rota principal**: Parser Python Universal (8 parsers em cascata). |
| `POST` | `/api/v1/importacoes/plano-saude/sorriso/analisar` | Parser IA (Gemini) específico para Sorriso Odonto. |
| `POST` | `/api/v1/importacoes/plano-saude/sorriso/confirmar` | Persistência da importação Sorriso Odonto. |
| `POST` | `/api/v1/importacoes/plano-saude/unimed-odonto/analisar` | Parser Python específico para Unimed Odonto. |
| `POST` | `/api/v1/importacoes/plano-saude/unimed-odonto/confirmar` | Persistência da importação Unimed Odonto. |

---

## 3. Parsers Determinísticos em Cascata (`IAService`)
O método `extrair_beneficiarios_pdf_universal()` executa **8 parsers sequenciais**. O primeiro que obtém sucesso é utilizado, evitando custos e latência de IA:

1. **`_fmt_unimed_single_line` (Formato A)**: Detecta matrícula `X.XXXXXXX.XXXXXXXX-X` (>= 5 ocorrências). Linhas com nome, matrícula, tipo T/D e CPF (formatado ou 11 dígitos).
2. **`_fmt_matricula_suffix` (Formato E - Analítico de Taxa Unimed)**: Detecta padrão `prefixo.partes-sufixo NOME TIPO RUBRICA valor`. Sufixo `00` = titular. Não possui CPF (`permite_fallback_nome = True`).
3. **`_fmt_seguro_vida` (Formato B)**: Marcadores `ALT/INC/EXC` com dígitos colados. Padrão `valor + matrícula + nome + tipo + CPF`.
4. **`_fmt_rubrica_multiline` (Formato A2 - Demonstrativo Analítico)**: Detecta rubricas específicas (Mensalidade, Prêmio, Retroativo) quebrando registros em múltiplas linhas.
5. **`_fmt_coparticipacao` (Formato H - Co-participação)**: Detecta `NOME - MATRÍCULA` e `TOTAL TITULAR`. Usa o total acumulado do PDF. Não tem CPF (`permite_fallback_nome = True`).
6. **`_fmt_responsavel` (Formato G)**: Blocos `Responsavel: <cod>` + `codigo NOME ... Valor Benef: valor`.
7. **`_fmt_sorriso_fragmented` (Formato F - Sorriso Odontológico via PyPDF)**: Detecta tipo `T` ou `D` isolado em sua própria linha (>= 5 ocorrências) devido à fragmentação de tabelas do PyPDF.
8. **`_fmt_generic` (Formato C - Genérico)**: Linha única com `NOME ... valor ... T/D`. Pula palavras reservadas (SUBTOTAL, TOTAL GERAL).

---

## 4. Fallback para IA (Gemini)
A Inteligência Artificial só é disparada se:
1. Nenhum beneficiário foi extraído pelos 8 parsers (ex: PDF escaneado ou layout inédito).
2. O total somado difere do total impresso no PDF em mais de 1% ou mais de R$ 1,00 (`_detectar_total_esperado()`).

---

## 5. Parser de Planilhas (CSV / Excel)
O método `extrair_beneficiarios_planilha()` processa arquivos `.xlsx`, `.xls` e `.csv`:
- Coluna B: Código do Titular (agrupador familiar).
- Coluna C: Tipo (`T` = titular, `D` = dependente).
- Coluna J: Valor da mensalidade.
- Coluna P: CPF do titular do grupo.

---

## 6. Resolução Hierárquica de Colaboradores
A vinculação do beneficiário ao colaborador do ERP segue regras estritas:
1. **CPF presente no documento**: Busca por `colaborador_repository.get_by_documento(cpf_11_digitos)`. Se não encontrar, **permanece sem vínculo** (nunca cai para nome para evitar homônimos).
2. **CPF ausente**: Consulta a tabela de aprendizado `colaborador_aliases` (`nome_divergente == nome_pdf`).
3. **Formatos sem CPF permitidos**: Usa nome normalizado (sem acentos, maiúsculas) com comparação exata.
4. **Sem correspondência**: Retorna `None`, permitindo vinculação manual pelo usuário na tela de conferência.

---

## 7. Sistema de Aprendizado Contínuo (Aliases)
- Na confirmação da importação, se o nome no PDF for diferente do nome do colaborador selecionado (`nome_pdf != colaborador.nome`), o sistema grava automaticamente a relação em `colaborador_aliases`.
- Nas faturas seguintes, essa variação passa a ser resolvida de forma 100% automática.

---

## 8. Regra de Negócio Crítica: Filtro de Colaboradores Ativos
- Em todas as etapas de busca, sugestão de IA e vinculação de faturas, devem ser considerados **apenas colaboradores com `snAtivo == 'S'`**.
