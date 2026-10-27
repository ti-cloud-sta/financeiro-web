export interface LancamentoHistorico {
  titulo: string;
  valor: number;
  dataVencimento: string;
  dataPagamento: string;
  diasAtraso: number;
  status: 'EM_DIA' | 'ATRASADO';
}

export interface HistoricoCliente {
  clienteCodigo: string;
  clienteNome: string;
  score: number;
  classificacao: string;
  titulosEmDia: number;
  titulosEmAtraso: number;
  percentualPontualidade: number;
  mediaDiasAtraso: number;
  valorTotalPago: number;
  lancamentos: LancamentoHistorico[];
}

export interface TituloMatrizItem {
  id: number;
  numeroDocumento?: string;
  valor: number;
  clienteCodigo?: number;
  clienteNome?: string;
  dataVencimento: string;
  banco: string;
  categoria: string;
  descricao: string;
}

export interface MatrizCardItem {
  idMatriz?: number;
  codigoMatriz?: string;
  nomeMatriz: string;
  banco: 'BANCO_DO_BRASIL' | 'ITAU' | 'PROVISAO';
  tipo: 'REAL' | 'PROVISAO';
  valorTotal: number;
  qtdTitulos: number;
  titulos: TituloMatrizItem[];
}

export interface TituloReceberMatrizItem {
  id: string | number;
  numeroDocumento?: string;
  valor: number;
  clienteCodigo?: string;
  clienteNome?: string;
  dataVencimento: string;
  modalidade: 'CARTEIRA' | 'BOLETO';
}

export interface MatrizReceberCardItem {
  idMatriz?: number;
  codigoMatriz?: string;
  nomeMatriz: string;
  modalidade: 'CARTEIRA' | 'BOLETO';
  valorTotal: number;
  qtdTitulos: number;
  score: number;
  classificacao: string;
  isNovo?: boolean;
  titulosEmDia: number;
  titulosEmAtraso: number;
  percentualPontualidade: number;
  mediaDiasAtraso: number;
  valorTotalPago: number;
  titulos: TituloReceberMatrizItem[];
  lancamentos: LancamentoHistorico[];
}

export interface ContaPagarItem {
  id: string | number;
  banco: 'BANCO_DO_BRASIL' | 'ITAU' | 'PROVISAO';
  favorecido: string;
  categoria: string;
  descricao: string;
  valor: number;
  dataVencimento: string;
  tipo: 'REAL' | 'PROVISAO';
  status: 'PENDENTE' | 'PROGRAMADO' | 'PAGO';
  numeroDocumento?: string;
  idMatriz?: number;
  codigoMatriz?: string;
  nomeMatriz?: string;
  clienteCodigo?: number;
  clienteNome?: string;
}

export interface ContaReceberItem {
  id: string;
  modalidade: 'CARTEIRA' | 'BOLETO';
  clienteCodigo: string;
  clienteNome: string;
  idMatriz?: number;
  codigoMatriz?: string;
  nomeMatriz?: string;
  documento: string;
  valor: number;
  dataVencimento: string;
  score: number; // 0 a 100
  historico: HistoricoCliente;
}

export const MOCK_HISTORICO_CLIENTES: Record<string, HistoricoCliente> = {
  'CLI-001': {
    clienteCodigo: 'CLI-001',
    clienteNome: 'Sendas Distribuidora (Assaí)',
    score: 95,
    classificacao: 'Excelente (Altíssima Previsibilidade)',
    titulosEmDia: 48,
    titulosEmAtraso: 2,
    percentualPontualidade: 96,
    mediaDiasAtraso: 0.8,
    valorTotalPago: 4280500.0,
    lancamentos: [
      { titulo: 'NF 10423/01', valor: 145000.0, dataVencimento: '15/10/2026', dataPagamento: '15/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10398/02', valor: 98400.0, dataVencimento: '08/10/2026', dataPagamento: '08/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10350/01', valor: 210000.0, dataVencimento: '01/10/2026', dataPagamento: '02/10/2026', diasAtraso: 1, status: 'ATRASADO' },
      { titulo: 'NF 10290/01', valor: 175200.0, dataVencimento: '22/09/2026', dataPagamento: '22/09/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10210/02', valor: 130000.0, dataVencimento: '15/09/2026', dataPagamento: '15/09/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-002': {
    clienteCodigo: 'CLI-002',
    clienteNome: 'Atacadão S/A',
    score: 91,
    classificacao: 'Excelente (Baixo Risco)',
    titulosEmDia: 39,
    titulosEmAtraso: 3,
    percentualPontualidade: 93,
    mediaDiasAtraso: 1.2,
    valorTotalPago: 3650000.0,
    lancamentos: [
      { titulo: 'NF 10411/01', valor: 182300.0, dataVencimento: '16/10/2026', dataPagamento: '16/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10375/01', valor: 144500.0, dataVencimento: '09/10/2026', dataPagamento: '09/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10320/02', valor: 96000.0, dataVencimento: '28/09/2026', dataPagamento: '30/09/2026', diasAtraso: 2, status: 'ATRASADO' },
      { titulo: 'NF 10260/01', valor: 205000.0, dataVencimento: '18/09/2026', dataPagamento: '18/09/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-003': {
    clienteCodigo: 'CLI-003',
    clienteNome: 'Mart Minas Distribuição Ltda',
    score: 84,
    classificacao: 'Bom (Previsibilidade Alta)',
    titulosEmDia: 26,
    titulosEmAtraso: 5,
    percentualPontualidade: 84,
    mediaDiasAtraso: 2.5,
    valorTotalPago: 1890000.0,
    lancamentos: [
      { titulo: 'NF 10405/01', valor: 76500.0, dataVencimento: '14/10/2026', dataPagamento: '14/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10360/01', valor: 88200.0, dataVencimento: '05/10/2026', dataPagamento: '08/10/2026', diasAtraso: 3, status: 'ATRASADO' },
      { titulo: 'NF 10310/01', valor: 65000.0, dataVencimento: '25/09/2026', dataPagamento: '25/09/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-004': {
    clienteCodigo: 'CLI-004',
    clienteNome: 'Supermercados Savegnago',
    score: 74,
    classificacao: 'Moderado (Atenção a Prazos)',
    titulosEmDia: 18,
    titulosEmAtraso: 8,
    percentualPontualidade: 69,
    mediaDiasAtraso: 4.8,
    valorTotalPago: 1120000.0,
    lancamentos: [
      { titulo: 'NF 10390/01', valor: 54000.0, dataVencimento: '10/10/2026', dataPagamento: '15/10/2026', diasAtraso: 5, status: 'ATRASADO' },
      { titulo: 'NF 10340/01', valor: 62500.0, dataVencimento: '30/09/2026', dataPagamento: '03/10/2026', diasAtraso: 3, status: 'ATRASADO' },
      { titulo: 'NF 10280/01', valor: 48000.0, dataVencimento: '18/09/2026', dataPagamento: '18/09/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-005': {
    clienteCodigo: 'CLI-005',
    clienteNome: 'Comercial Zeferino Ltda',
    score: 63,
    classificacao: 'Atenção (Histórico Frequente de Prorrogação)',
    titulosEmDia: 11,
    titulosEmAtraso: 9,
    percentualPontualidade: 55,
    mediaDiasAtraso: 7.4,
    valorTotalPago: 780000.0,
    lancamentos: [
      { titulo: 'NF 10385/01', valor: 42000.0, dataVencimento: '12/10/2026', dataPagamento: '20/10/2026', diasAtraso: 8, status: 'ATRASADO' },
      { titulo: 'NF 10315/01', valor: 38500.0, dataVencimento: '24/09/2026', dataPagamento: '02/10/2026', diasAtraso: 8, status: 'ATRASADO' },
      { titulo: 'NF 10245/01', valor: 35000.0, dataVencimento: '10/09/2026', dataPagamento: '10/09/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-006': {
    clienteCodigo: 'CLI-006',
    clienteNome: 'Rede Droga Raia / Drogasil',
    score: 97,
    classificacao: 'Excelente (Altíssima Previsibilidade)',
    titulosEmDia: 32,
    titulosEmAtraso: 1,
    percentualPontualidade: 97,
    mediaDiasAtraso: 0.3,
    valorTotalPago: 2450000.0,
    lancamentos: [
      { titulo: 'NF 10430/01', valor: 112000.0, dataVencimento: '17/10/2026', dataPagamento: '17/10/2026', diasAtraso: 0, status: 'EM_DIA' },
      { titulo: 'NF 10370/01', valor: 95000.0, dataVencimento: '04/10/2026', dataPagamento: '04/10/2026', diasAtraso: 0, status: 'EM_DIA' }
    ]
  },
  'CLI-007': {
    clienteCodigo: 'CLI-007',
    clienteNome: 'Supermercado Progresso ABC',
    score: 52,
    classificacao: 'Risco Alto (Atrasos Crônicos)',
    titulosEmDia: 6,
    titulosEmAtraso: 10,
    percentualPontualidade: 37,
    mediaDiasAtraso: 11.2,
    valorTotalPago: 320000.0,
    lancamentos: [
      { titulo: 'NF 10378/01', valor: 28900.0, dataVencimento: '08/10/2026', dataPagamento: '21/10/2026', diasAtraso: 13, status: 'ATRASADO' },
      { titulo: 'NF 10302/01', valor: 31200.0, dataVencimento: '20/09/2026', dataPagamento: '05/10/2026', diasAtraso: 15, status: 'ATRASADO' }
    ]
  }
};

export const MOCK_CONTAS_PAGAR: ContaPagarItem[] = [
  // Banco do Brasil
  {
    id: 'CP-001',
    banco: 'BANCO_DO_BRASIL',
    favorecido: 'Química Santo Antônio Ltda',
    categoria: 'Matéria Prima',
    descricao: 'Fornecimento Ácido Sulfônico / Soda Líquida',
    valor: 184500.0,
    dataVencimento: '23/10/2026',
    tipo: 'REAL',
    status: 'PROGRAMADO',
    numeroDocumento: 'DUP 45892/01'
  },
  {
    id: 'CP-002',
    banco: 'BANCO_DO_BRASIL',
    favorecido: 'Braskem Polímeros S/A',
    categoria: 'Matéria Prima',
    descricao: 'Resinas Plásticas para Frascos e Tampas',
    valor: 265000.0,
    dataVencimento: '24/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'DUP 98450/02'
  },
  {
    id: 'CP-003',
    banco: 'BANCO_DO_BRASIL',
    favorecido: 'EDP Espírito Santo Distribuição',
    categoria: 'Utilidades',
    descricao: 'Energia Elétrica Industrial - Matriz Colatina',
    valor: 92450.0,
    dataVencimento: '25/10/2026',
    tipo: 'REAL',
    status: 'PROGRAMADO',
    numeroDocumento: 'FAT 202610-09'
  },
  {
    id: 'CP-004',
    banco: 'BANCO_DO_BRASIL',
    favorecido: 'Transportadora Carga Segura',
    categoria: 'Logística & Fretes',
    descricao: 'Frete de Transferência Filial Linhares',
    valor: 48900.0,
    dataVencimento: '25/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'CTE 12049'
  },
  {
    id: 'CP-005',
    banco: 'BANCO_DO_BRASIL',
    favorecido: 'Smurfit Kappa Embalagens',
    categoria: 'Embalagens',
    descricao: 'Caixas de Papelão Ondulado Desinfetante',
    valor: 73200.0,
    dataVencimento: '26/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'DUP 77410/01'
  },

  // Itaú
  {
    id: 'CP-006',
    banco: 'ITAU',
    favorecido: 'Folha de Pagamento - Adiantamento',
    categoria: 'Recursos Humanos',
    descricao: 'Adiantamento Quinzenal Colaboradores',
    valor: 340000.0,
    dataVencimento: '24/10/2026',
    tipo: 'REAL',
    status: 'PROGRAMADO',
    numeroDocumento: 'FOLHA-202610'
  },
  {
    id: 'CP-007',
    banco: 'ITAU',
    favorecido: 'Unimed Vitória Cooperativa Médica',
    categoria: 'Benefícios',
    descricao: 'Fatura Plano de Saúde Colaboradores',
    valor: 118400.0,
    dataVencimento: '25/10/2026',
    tipo: 'REAL',
    status: 'PROGRAMADO',
    numeroDocumento: 'FAT-MED-1026'
  },
  {
    id: 'CP-008',
    banco: 'ITAU',
    favorecido: 'Givaudan Fragrâncias Brasil',
    categoria: 'Matéria Prima',
    descricao: 'Fragrâncias e Essências Linha Limpeza',
    valor: 156300.0,
    dataVencimento: '26/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'DUP 33019/03'
  },
  {
    id: 'CP-009',
    banco: 'ITAU',
    favorecido: 'Totvs S/A - Licenciamento ERP',
    categoria: 'Tecnologia / TI',
    descricao: 'Mensalidade e Manutenção Datasul 12',
    valor: 38200.0,
    dataVencimento: '27/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'NFSe 88401'
  },
  {
    id: 'CP-010',
    banco: 'ITAU',
    favorecido: 'Petrobras Distribuidora S/A',
    categoria: 'Combustíveis',
    descricao: 'Abastecimento Frota de Caminhões',
    valor: 64800.0,
    dataVencimento: '28/10/2026',
    tipo: 'REAL',
    status: 'PENDENTE',
    numeroDocumento: 'DUP 12904/01'
  },

  // Provisões
  {
    id: 'PR-001',
    banco: 'PROVISAO',
    favorecido: 'Provisão 13º Salário (1ª Parcela)',
    categoria: 'Provisão Trabalhista',
    descricao: '1ª Parcela do 13º Salário da Produção e Adm',
    valor: 240000.0,
    dataVencimento: '30/11/2026',
    tipo: 'PROVISAO',
    status: 'PENDENTE',
    numeroDocumento: 'PROV-13SAL'
  },
  {
    id: 'PR-002',
    banco: 'PROVISAO',
    favorecido: 'Provisão Tributos Federais (PIS/COFINS)',
    categoria: 'Provisão Fiscal',
    descricao: 'Estimativa de DARF PIS/COFINS sobre Faturamento',
    valor: 135000.0,
    dataVencimento: '25/11/2026',
    tipo: 'PROVISAO',
    status: 'PENDENTE',
    numeroDocumento: 'PROV-PISCOFINS'
  },
  {
    id: 'PR-003',
    banco: 'PROVISAO',
    favorecido: 'Provisão Comissões Representantes Comerciais',
    categoria: 'Provisão Comercial',
    descricao: 'Comissões de Vendas a Liquidar Fechamento do Mês',
    valor: 85500.0,
    dataVencimento: '10/11/2026',
    tipo: 'PROVISAO',
    status: 'PENDENTE',
    numeroDocumento: 'PROV-COMIS'
  },
  {
    id: 'PR-004',
    banco: 'PROVISAO',
    favorecido: 'Provisão Manutenção Preventiva Caldeiras',
    categoria: 'Provisão Operacional',
    descricao: 'Parada programada para revisão da Caldeira 02',
    valor: 45000.0,
    dataVencimento: '15/11/2026',
    tipo: 'PROVISAO',
    status: 'PENDENTE',
    numeroDocumento: 'PROV-MANUT'
  }
];

export const MOCK_CONTAS_RECEBER: ContaReceberItem[] = [
  // Carteira (Transferências / TED / PIX direto)
  {
    id: 'CR-001',
    modalidade: 'CARTEIRA',
    clienteCodigo: 'CLI-001',
    clienteNome: 'Sendas Distribuidora (Assaí)',
    documento: 'NF 10488/01',
    valor: 320500.0,
    dataVencimento: '24/10/2026',
    score: 95,
    historico: MOCK_HISTORICO_CLIENTES['CLI-001']
  },
  {
    id: 'CR-002',
    modalidade: 'CARTEIRA',
    clienteCodigo: 'CLI-002',
    clienteNome: 'Atacadão S/A',
    documento: 'NF 10492/01',
    valor: 285400.0,
    dataVencimento: '25/10/2026',
    score: 91,
    historico: MOCK_HISTORICO_CLIENTES['CLI-002']
  },
  {
    id: 'CR-003',
    modalidade: 'CARTEIRA',
    clienteCodigo: 'CLI-006',
    clienteNome: 'Rede Droga Raia / Drogasil',
    documento: 'NF 10505/01',
    valor: 194800.0,
    dataVencimento: '26/10/2026',
    score: 97,
    historico: MOCK_HISTORICO_CLIENTES['CLI-006']
  },
  {
    id: 'CR-004',
    modalidade: 'CARTEIRA',
    clienteCodigo: 'CLI-004',
    clienteNome: 'Supermercados Savegnago',
    documento: 'NF 10470/02',
    valor: 118200.0,
    dataVencimento: '27/10/2026',
    score: 74,
    historico: MOCK_HISTORICO_CLIENTES['CLI-004']
  },
  {
    id: 'CR-005',
    modalidade: 'CARTEIRA',
    clienteCodigo: 'CLI-007',
    clienteNome: 'Supermercado Progresso ABC',
    documento: 'NF 10461/01',
    valor: 46900.0,
    dataVencimento: '28/10/2026',
    score: 52,
    historico: MOCK_HISTORICO_CLIENTES['CLI-007']
  },

  // Boleto (Cobrança Bancária)
  {
    id: 'CR-006',
    modalidade: 'BOLETO',
    clienteCodigo: 'CLI-002',
    clienteNome: 'Atacadão S/A',
    documento: 'BOL 49811/02',
    valor: 412000.0,
    dataVencimento: '24/10/2026',
    score: 91,
    historico: MOCK_HISTORICO_CLIENTES['CLI-002']
  },
  {
    id: 'CR-007',
    modalidade: 'BOLETO',
    clienteCodigo: 'CLI-001',
    clienteNome: 'Sendas Distribuidora (Assaí)',
    documento: 'BOL 49830/01',
    valor: 275000.0,
    dataVencimento: '25/10/2026',
    score: 95,
    historico: MOCK_HISTORICO_CLIENTES['CLI-001']
  },
  {
    id: 'CR-008',
    modalidade: 'BOLETO',
    clienteCodigo: 'CLI-003',
    clienteNome: 'Mart Minas Distribuição Ltda',
    documento: 'BOL 49815/01',
    valor: 168400.0,
    dataVencimento: '26/10/2026',
    score: 84,
    historico: MOCK_HISTORICO_CLIENTES['CLI-003']
  },
  {
    id: 'CR-009',
    modalidade: 'BOLETO',
    clienteCodigo: 'CLI-005',
    clienteNome: 'Comercial Zeferino Ltda',
    documento: 'BOL 49790/01',
    valor: 89300.0,
    dataVencimento: '27/10/2026',
    score: 63,
    historico: MOCK_HISTORICO_CLIENTES['CLI-005']
  },
  {
    id: 'CR-010',
    modalidade: 'BOLETO',
    clienteCodigo: 'CLI-003',
    clienteNome: 'Mart Minas Distribuição Ltda',
    documento: 'BOL 49844/02',
    valor: 142000.0,
    dataVencimento: '28/10/2026',
    score: 84,
    historico: MOCK_HISTORICO_CLIENTES['CLI-003']
  }
];

export const MOCK_VALOR_INVESTIDO_RESGATAVEL = 350000.0;

export interface AtualizacaoHistoryItem {
  id: string;
  dataHora: string;
  nomeArquivo: string;
  tipo: string;
  autor: string;
  idImportacoes?: number;
}

export const MOCK_ATUALIZACOES_CAIXA: AtualizacaoHistoryItem[] = [
  {
    id: 'AT-001',
    dataHora: '21/10/2026 18:30',
    nomeArquivo: 'CONTAS_PAGAR_21102026.xlsx',
    tipo: 'CONTAS A PAGAR (APB)',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-002',
    dataHora: '21/10/2026 18:25',
    nomeArquivo: 'CONTAS_RECEBER_21102026.xlsx',
    tipo: 'CONTAS A RECEBER (ACR)',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-003',
    dataHora: '21/10/2026 18:20',
    nomeArquivo: 'TITULOS_LIQUIDADOS_OUTUBRO.xlsx',
    tipo: 'TITULOS LIQUIDADOS',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-004',
    dataHora: '20/10/2026 16:45',
    nomeArquivo: 'APLICACOES_RESGATE_20102026.xlsx',
    tipo: 'INVESTIMENTOS',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-005',
    dataHora: '19/10/2026 15:40',
    nomeArquivo: 'CONTAS_PAGAR_19102026.xlsx',
    tipo: 'CONTAS A PAGAR (APB)',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-006',
    dataHora: '18/10/2026 14:15',
    nomeArquivo: 'CONTAS_RECEBER_18102026.xlsx',
    tipo: 'CONTAS A RECEBER (ACR)',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-007',
    dataHora: '17/10/2026 11:20',
    nomeArquivo: 'TITULOS_LIQUIDADOS_PROJETADOS.xlsx',
    tipo: 'TITULOS LIQUIDADOS',
    autor: 'Tania Canedo Blanca'
  },
  {
    id: 'AT-008',
    dataHora: '16/10/2026 09:30',
    nomeArquivo: 'EXTRATO_CONSOLIDADO_OUT.xlsx',
    tipo: 'INVESTIMENTOS',
    autor: 'Tania Canedo Blanca'
  }
];


