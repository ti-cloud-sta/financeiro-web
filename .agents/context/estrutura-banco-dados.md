# Contexto Estrutural: Banco de Dados MySQL (`stamariabd`)

Mapeamento da arquitetura de tabelas, entidades e views do banco de dados da aplicação.

---

## 1. Mapeamento de Tabelas Principais

### Colaboradores e RH
- `colaboradores`: Dados cadastrais principais (id, nome em maiúsculas, CPF, status `snAtivo`).
- `colaboradoresmovimento`: Histórico de movimentações funcionais e alterações de status (ex: `ATIVACAO`).
- `colaboradoralias`: Variações, abreviações e apelidos de colaboradores para reconhecimento inteligente em faturas de convênios.
- `tipocolaborador` & `cargos_colaboradores`: Classificação e cargos dos profissionais.

### Inadimplência e Cobrança
- `nfpendencias`: Registro principal de títulos e notas pendentes de pagamento (chave composta: Unidade, Série, Título, Parcela, Espécie, Carteira; status `encerrado = 'S'`, `'P'` ou `'N'`).
- `historicopendencia`: Linha do tempo de todas as alterações sofridas pelo título (importações, atualizações de saldo, mudanças de carteira, prorrogações e baixa).
- `tratativas`: Ações de cobrança e contatos registrados com os devedores.
- `tratativapendencia`: Associação N:N entre tratativas realizadas e títulos pendentes.
- `pendencia_mensagem`: Mensagens e notificações atreladas a uma pendência.

### Cadastros Base e Organização
- `empresas`: Entidades jurídicas do grupo Santa Maria.
- `unidade`: Filiais e unidades operacionais.
- `centrocusto`: Centros de custos analíticos e sintéticos.
- `centroestado`: Vínculo entre centros de custos e estados de atuação.
- `modulos` & `empresamodulo`: Controle de módulos ativos por empresa contratante.

### Clientes e Matrizes
- `clientes`: Dados cadastrais de clientes e sacados.
- `matrizcliente`: Agrupamentos e matrizes de relacionamento de clientes.
- `cliente_representante`: Vínculo entre clientes e seus representantes comerciais responsáveis.

### Auditoria, Usuários e Importações
- `importacoes`: Log e metadados de cada arquivo importado no sistema (PDFs, planilhas, faturas).
- `movimentacoes`: Lançamentos financeiros e conciliações.
- `users`, `roles`, `userrole`: Autenticação, perfis de acesso e autorização no sistema.

---

## 2. Views do Sistema (Single Source of Truth)
- `vw_nfpendencias_fase`: View oficial que computa dinamicamente a `Fase` e o `Status` de cada pendência com base na carteira, datas de vencimento, prorrogação e encerramento. O backend consulta essa view após cada inserção para assegurar integridade absoluta sem replicar regras no código.
