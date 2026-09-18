# Regras Legadas do Endpoint /importacoes/inadimplencia/importar-pendencias

Este documento descreve as regras de negócio originais do endpoint de importação de pendências antes da refatoração. O endpoint recebia um arquivo `.xlsx` (geralmente extraído do ERP) e executava a leitura, validação e classificação das pendências para o módulo de inadimplência.

## 1. Validações Iniciais e Filtros
- **Formato da Planilha:** A planilha precisava conter no mínimo **21 colunas** (indo da coluna A até a coluna U). O processo falhava se houvesse menos colunas.
- **Linhas Ignoradas (Bypassed):** O script lia o Excel linha a linha e ignorava inserções caso:
  - A linha estivesse em branco ou fosse rodapé (detectado se a coluna B "Espécie" estivesse vazia).
  - Faltasse a Data de Vencimento (coluna P).
  - Faltasse as informações do Cliente (código ou nome).
- **Cadastro Automático (Upsert):** Se um código ou nome de cliente (e matriz) fosse lido e ainda não existisse no banco de dados do sistema, eles eram criados e vinculados automaticamente durante a varredura da linha.
- **Prevenção de Duplicidade Simples (Regra Legada):** O sistema validava a existência baseando-se na chave composta de `Unidade + Série + Título + Parcela`. Se a pendência já existisse com estes atributos, a linha era ignorada para evitar duplicação em banco. *(Nota de Atualização: A regra atual considera `Unidade + Série + Título + Parcela + Espécie + Carteira` para permitir coexistência de espécies diferentes no mesmo título e atualizações de saldo/carteira, conforme detalhado em `CONTEXTO_MODULOS.md` e `AGENTS.md`)*.

## 2. Regras de Classificação e Triagem Automática
Durante a importação, cada nota era classificada (designada a uma **Fase** e **Status**) baseada na primeira regra que retornasse verdadeiro dentre a cascata abaixo:

*Referência das colunas da planilha:* 
- `B`: Espécie
- `G`: Tipo de Pedido
- `M`: Carteira
- `O`: Dt. de Entrega (se preenchida ou não)
- `T`: Valor Original
- `U`: Saldo

**Logística**
- Fase `LOGISTICA` / Status `DEVOLUCAO`: Espécie "DP" e Carteira "DEV".
- Fase `LOGISTICA` / Status `SEM DATA DE ENTREGA`: Espécie "DP", Tipo de Pedido "PV" e data de entrega VAZIA.

**Comercial**
- Fase `COMERCIAL` / Status `ACORDO`: Espécie "DP", Tipo de Pedido "PV", Carteira "CAR", com data de entrega preenchida, E Saldo menor que Valor Original.

**Fiscal**
- Fase `FISCAL` / Status `COMISSAO`: Espécie "DP", Tipo de Pedido "ER", Carteira "CAR", com data de entrega preenchida, E Saldo menor que Valor Original.

**Financeiro**
- Fase `FINANCEIRO` / Status `ATRASADO`: Espécie "DP", Tipo de Pedido "PV", Carteira igual a "SIM" ou "VIN", com data de entrega preenchida.

**Pendências (Gerais)**
- Fase `PENDENCIAS` / Status `AD`: Espécie "AD".
- Fase `PENDENCIAS` / Status `AN`: Espécie "AN".
- Fase `PENDENCIAS` / Status `EXPORTACAO`: Espécie "DP", Tipo de Pedido "PX", sem data de entrega.
- Fase `PENDENCIAS` / Status `MARTINS`: Espécie "DP", Tipo de Pedido "ER", sem data de entrega.
- Fase `PENDENCIAS` / Status `MERCADINHO`: Espécie "DP", Tipo de Pedido "E1", sem data de entrega.
- Fase `PENDENCIAS` / Status `DES`: Espécie "DP", Tipo de Pedido "PV", Carteira "DES", com data de entrega preenchida.
- Fase `PENDENCIAS` / Status `PR`: Espécie "PR".
- Fase `PENDENCIAS` / Status `RJ`: Espécie "RJ".

**Triagem Manual (Fallback)**
- Fase `PENDENCIAS` / Status `ANALISAR`: Caso a linha importada passasse nas validações mas não atingisse nenhuma das condicionais acima, ela assumia este status para que o usuário resolvesse na tela.

## 3. Conciliação de Baixas / Finalização Automática
O sistema realizava uma técnica de espelhamento com o ERP de origem:
- Ao finalizar a varredura e inserção de todas as linhas da planilha enviada, o sistema buscava no banco de dados todas as pendências que ainda estivessem em aberto (fase diferente de "FINALIZADO").
- O script avaliava se a pendência existia dentro do arquivo `.xlsx` recebido.
- Se a pendência aberta no banco **NÃO** estivesse entre as chaves contidas no Excel recém lido, o backend presumia que ela havia sido paga ou baixada no ERP oficial da empresa. Assim, alterava a fase dela para `FINALIZADO` de forma automática.

## 4. Auditoria e Rastreio
- Toda inserção criava um log de histórico no banco de dados atrelado à nota registrando *"Pendência Importada"* e explicando qual fase foi designada.
- As baixas automáticas do processo de conciliação descritas acima geravam um histórico denominado *"Finalização Automática"*.
