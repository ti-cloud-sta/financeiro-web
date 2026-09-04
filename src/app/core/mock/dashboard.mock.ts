import { LastAccess, SummaryCard } from '../models/dashboard.model';

export const MOCK_SUMMARY_CARDS: SummaryCard[] = [
  {
    id: 'sum-1',
    title: 'Vendas do Mês',
    value: 'R$ 124.500',
    icon: '📈',
    trend: 'up',
    trendValue: '+15%',
    colorClass: 'success'
  },
  {
    id: 'sum-2',
    title: 'Novos Clientes',
    value: 48,
    icon: '👥',
    trend: 'up',
    trendValue: '+5%',
    colorClass: 'primary'
  },
  {
    id: 'sum-3',
    title: 'Contas em Atraso',
    value: 12,
    icon: '⚠️',
    trend: 'down',
    trendValue: '-2%',
    colorClass: 'danger'
  },
  {
    id: 'sum-4',
    title: 'Pedidos Pendentes',
    value: 8,
    icon: '📦',
    trend: 'neutral',
    trendValue: '0%',
    colorClass: 'warning'
  }
];

export const MOCK_LAST_ACCESSES: LastAccess[] = [
  {
    id: 'la-1',
    label: 'Funil de Vendas',
    route: '/crm/pipeline',
    icon: 'fa-solid fa-handshake',
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() // 15 mins atrás
  },
  {
    id: 'la-2',
    label: 'Cadastro de Clientes',
    route: '/crm/customers',
    icon: '👥',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString() // 2 horas atrás
  },
  {
    id: 'la-3',
    label: 'Contas a Pagar',
    route: '/finance/payable',
    icon: '💸',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString() // Ontem
  }
];
