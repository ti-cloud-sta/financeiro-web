import { MenuItem } from '../models/menu.model';

export const MOCK_MENU: MenuItem[] = [
  {
    id: 'menu-home',
    label: 'Dashboard',
    icon: 'fa-solid fa-house',
    route: '/home',
    order: 1,
    isFavorite: true
  },
  {
    id: 'menu-crm',
    label: 'CRM & Vendas',
    icon: 'fa-solid fa-handshake',
    order: 2,
    requiredPermissions: ['sales:read'],
    children: [
      {
        id: 'menu-crm-pipeline',
        label: 'Funil de Vendas',
        route: '/crm/pipeline',
        order: 1
      },
      {
        id: 'menu-crm-customers',
        label: 'Clientes',
        route: '/crm/customers',
        order: 2
      }
    ]
  },
  {
    id: 'menu-finance',
    label: 'Financeiro',
    icon: 'fa-solid fa-wallet',
    order: 3,
    requiredPermissions: ['finance:full'],
    children: [
      {
        id: 'menu-fin-payable',
        label: 'Contas a Pagar',
        route: '/finance/payable',
        order: 1
      },
      {
        id: 'menu-fin-receivable',
        label: 'Contas a Receber',
        route: '/finance/receivable',
        order: 2
      }
    ]
  },
  {
    id: 'menu-extratores',
    label: 'Extratores',
    icon: 'fa-solid fa-file-import',
    route: '/extratores',
    order: 4
  },
  {
    id: 'menu-settings',
    label: 'Configurações',
    icon: 'fa-solid fa-gear',
    route: '/settings',
    order: 99,
    requiredPermissions: ['users:read']
  }
];
