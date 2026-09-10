import { MenuItem } from '../models/menu.model';

export const MOCK_MENU: MenuItem[] = [
  // {
  //   id: 'menu-home',
  //   label: 'Dashboard',
  //   icon: 'fa-solid fa-house',
  //   route: '/home',
  //   order: 1,
  //   isFavorite: true
  // },
  // {
  //   id: 'menu-crm',
  //   label: 'CRM & Vendas',
  //   icon: 'fa-solid fa-handshake',
  //   order: 2,
  //   requiredPermissions: ['sales:read'],
  //   children: [
  //     {
  //       id: 'menu-crm-pipeline',
  //       label: 'Funil de Vendas',
  //       route: '/crm/pipeline',
  //       order: 1
  //     },
  //     {
  //       id: 'menu-crm-customers',
  //       label: 'Clientes',
  //       route: '/crm/customers',
  //       order: 2
  //     }
  //   ]
  // },
  // {
  //   id: 'menu-finance',
  //   label: 'Financeiro',
  //   icon: 'fa-solid fa-wallet',
  //   order: 3,
  //   requiredPermissions: ['finance:full'],
  //   children: [
  //     {
  //       id: 'menu-fin-payable',
  //       label: 'Contas a Pagar',
  //       route: '/finance/payable',
  //       order: 1
  //     },
  //     {
  //       id: 'menu-fin-receivable',
  //       label: 'Contas a Receber',
  //       route: '/finance/receivable',
  //       order: 2
  //     }
  //   ]
  // },
  // {
  //   id: 'menu-extratores',
  //   label: 'Extratores',
  //   icon: 'fa-solid fa-file-import',
  //   route: '/extratores',
  //   order: 4
  // },
  {
    id: 'menu-plano-saude',
    label: 'Plano de Saúde',
    icon: 'fa-solid fa-heart-pulse',
    route: '/plano-saude',
    order: 1
  },
  {
    id: 'menu-despesas-viagens',
    label: 'Despesas de Viagens',
    icon: 'fa-solid fa-plane-departure',
    route: '/despesas-viagens',
    order: 2
  },
  {
    id: 'menu-extratores',
    label: 'Extratores',
    icon: 'fa-solid fa-file-import',
    route: '/extratores',
    order: 3
  },
  // {
  //   id: 'menu-inadimplencia',
  //   label: 'Inadimplência',
  //   icon: 'fa-solid fa-file-invoice-dollar',
  //   route: '/inadimplencia',
  //   order: 4
  // },
  {
    id: 'menu-conciliacao-pagamentos',
    label: 'Conciliação de Pagamentos',
    icon: 'fa-solid fa-scale-balanced',
    route: '/conciliacao-pagamentos',
    order: 5
  },
  {
    id: 'menu-settings',
    label: 'Configurações e Cadastros',
    icon: 'fa-solid fa-gear',
    route: '/configuracoes-cadastros',
    order: 2,
    requiredPermissions: ['users:read']
  }
];
