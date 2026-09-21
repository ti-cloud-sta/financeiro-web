# Diretrizes de Banco de Dados e Scripts SQL

Regras para interação com o banco de dados MySQL e proteção de dumps e schemas.

---

## 1. Proibição Absoluta de Alteração em Arquivos SQL
- **É estritamente proibido** ao assistente modificar qualquer arquivo `.sql` no projeto (como os dumps existentes em `databse/dumps/` ou na pasta `files/`).
- Esses arquivos representam backups de estrutura e dados fornecidos exclusivamente para referência.
- **Toda e qualquer alteração no banco de dados (criação de tabelas, alteração de colunas, views, triggers e rotinas) deve ser executada exclusivamente pelo usuário**.
- O assistente deve fornecer os comandos SQL necessários no chat ou em instruções para o usuário executar no seu próprio cliente MySQL.

---

## 2. Views como "Single Source of Truth" (Fonte Única da Verdade)
- Regras complexas de definição de negócio, como a classificação de **Fase** e **Status** de pendências de inadimplência, residem centralizadas nas views do banco de dados (ex: `vw_nfpendencias_fase`).
- O código Python (backend) **não deve replicar** essa lógica manualmente. Em vez disso:
  1. Insere ou atualiza o registro na tabela física.
  2. Executa `db.flush()` para sincronizar a transação ativa.
  3. Consulta a view correspondente na mesma sessão para recuperar a fase e status oficiais gerados pelo banco de dados.
  4. Registra os históricos com base no resultado da view.
