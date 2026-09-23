# Integração Contínua, Builds e Testes

Regras de validação obrigatória antes da conclusão de qualquer tarefa.

---

## 1. Build de Validação Obrigatório
- **Regra**: Sempre executar uma validação de compilação completa (`npm run build` na pasta `frontend/`) e aguardar sua conclusão antes de declarar uma macro-tarefa como finalizada.
- **Tolerância Zero para Falhas de Compilação**: Tarefas com erros de compilação do TypeScript, template errors do Angular (`NG5002`, `NG8002`, etc.) ou estouro de sintaxe SCSS não podem ser entregues.

---

## 2. Testes de Integração (CI)
- Após a finalização bem-sucedida do build, executar os testes de integração com Cypress:
  ```bash
  npm run cy:run
  ```
- Aguardar a execução completa dos testes e inspecionar o relatório de testes para garantir que nenhuma regressão foi introduzida em fluxos já existentes.
