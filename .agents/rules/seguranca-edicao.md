# Regras de Segurança de Edição de Código e Prevenção de Perda de Dados

> **REGRA CRÍTICA INEGOCIÁVEL**: Estas diretrizes visam impedir acidentes de perda de código, quebra de templates ou corrupção de arquivos durante o desenvolvimento com IA.

---

## 1. Proibição Absoluta de Scripts Automáticos para Editar Código
- **É expressamente proibido** criar ou executar scripts externos (Python, Node.js, Bash, PowerShell ou Regex) para "fatiar", "fazer merge", "concatenar" ou reescrever arquivos de template HTML, folhas de estilo SCSS ou scripts TypeScript/JavaScript.
- **Ferramentas Oficiais**: Toda e qualquer alteração no código-fonte do projeto deve ser feita **exclusivamente** através das ferramentas oficiais do assistente (`replace_file_content` ou `multi_replace_file_content`).

---

## 2. Edições Cirúrgicas e Pontuais
- As modificações devem ser mínimas e focadas estritamente nas linhas necessárias (trechos de 5 a 15 linhas).
- **Proibição de Substituições Massivas**: É terminantemente proibido substituir blocos de centenas de linhas de uma vez só ou tentar sobrescrever arquivos inteiros (`write_to_file` com `Overwrite: true`) quando o objetivo for um ajuste local (ex: ajustar um badge, classe, botão ou estilo).
- Se uma página for extensa, localize o elemento exato e substitua apenas a tag ou bloco circunscrito.

---

## 3. Cuidado com Arquivos Longos e Limite de Leitura (Truncamento)
- Em arquivos com muitas centenas ou milhares de linhas (como dashboards ou cadastros completos), a visualização inicial (`view_file`) pode truncar o conteúdo devido ao limite de bytes.
- **Nunca assuma o conteúdo faltante**: O assistente jamais deve inferir código faltante ou assumir que o arquivo termina onde a visualização foi cortada.
- Sempre inspecione o intervalo de linhas específico com `StartLine` e `EndLine` antes de aplicar qualquer alteração.

---

## 4. Localização de Git e Histórico Local do IDE (Recuperação de Emergência)
Em qualquer suspeita de perda de dados, corrupção de template ou necessidade de reverter alterações:
- **Executável Git**: O Git da máquina está localizado em:
  `C:\Users\JOE\AppData\Local\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`
- **Histórico Local do IDE (Local History / Timeline)**: O IDE mantém um backup histórico automático a cada salvamento em:
  `%APPDATA%\Antigravity IDE\User\History\`
- Sempre recorra a essas fontes de restauração antes de tentar recriações manuais arriscadas.

---

## 5. Política de Lixo Zero (Limpeza Obrigatória)
- Nenhum arquivo temporário gerado durante análises, testes ou diagnósticos deve permanecer no repositório.
- Arquivos como `test_*.py`, `scratch_*.py`, `*.backup`, `*.fixed`, `*.tmp`, dumps ou anotações temporárias devem ser **deletados imediatamente** antes de encerrar o turno de trabalho.
