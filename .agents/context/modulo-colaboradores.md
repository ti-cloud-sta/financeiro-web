# Contexto de Negócio: Módulo de Colaboradores

Regras de negócio, integridade cadastral e políticas de prevenção de duplicidade para colaboradores.

---

## 1. Regra de Anti-Duplicidade e Reativação
- **Validação Exclusiva por CPF**: Ao cadastrar ou importar colaboradores (`ColaboradorService.create_colaborador`), a verificação de existência prévia de colaboradores ativos ou inativos deve ser feita **estritamente pelo número do CPF/Documento**.
- **Proibição de Merge por Nome**: É expressamente proibido mesclar cadastros inativos baseando-se apenas no nome do colaborador. Isso previne a fusão indevida e corrupção de cadastros de pessoas homônimas.
- **Fluxo de Reativação**: Caso o CPF já exista e pertença a um colaborador inativo (`snAtivo = 'N'`), o sistema não cria uma linha nova; em vez disso:
  1. Atualiza as informações cadastrais.
  2. Altera o status para ativo (`snAtivo = 'S'`).
  3. Registra obrigatoriamente um movimento de `ATIVACAO` na tabela `colaboradoresmovimento`.

---

## 2. Padronização Obrigatória de Nomes (Uppercase)
- Todos os nomes de colaboradores devem ser armazenados no banco de dados em **LETRAS MAIÚSCULAS**.
- Essa padronização é garantida na camada de entrada através de `@field_validator` na classe `ColaboradorBase` do Pydantic, garantindo consistência independente da origem do cadastro (manual, planilha ou PDF).

---

## 3. Fluxo Único de Criação (Camada Service)
- Processamentos em lote (importações de planilhas de RH, despesas ou convênios) **nunca devem instanciar a entidade `Colaborador` e fazer `db.add()` diretamente**.
- Toda criação ou reativação deve ser obrigatoriamente roteada através de `ColaboradorService.create_colaborador`. Isso assegura que:
  - As travas anti-duplicidade por CPF sejam respeitadas.
  - A formatação uppercase seja aplicada.
  - O histórico de movimentação (`colaboradoresmovimento`) seja fielmente gravado.

---

## 4. Gestão Contínua de Apelidos (Aliases)
- Faturas de terceiros frequentemente trazem abreviações ou variações de nomes.
- A tabela `colaboradoralias` armazena essas variações vinculadas ao colaborador principal, permitindo reconhecimento automático em importações subsequentes.
