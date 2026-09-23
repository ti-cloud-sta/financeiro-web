# Contexto de Negócio: Módulo de Conciliação de Pagamentos

Regras de negócio e rotinas de conciliação bancária e financeira.

---

## 1. Fluxo de Conciliação Bancária
- O módulo é responsável por confrontar os lançamentos de extratos bancários com os títulos a pagar e baixas registradas no ERP.
- Permite a importação de arquivos bancários e a conferência passo a passo dos lançamentos conciliados, divergentes ou pendentes.

---

## 2. Auditoria e Rastreabilidade
- Cada conciliação gravada vincula os IDs das movimentações com os comprovantes bancários, garantindo rastreabilidade contábil e auditoria financeira completa.
- O padrão visual segue as tabelas SaaS sem bordas verticais, com valores com alinhamento tabular à direita (`tabular-nums`) e badges coloridos para os status de conciliação.
