import { AppModule } from '../models/module.model';

export const MOCK_MODULES: AppModule[] = [
  {
    id: 'mod-health',
    name: 'Plano de Saúde',
    icon: 'fa-solid fa-heart-pulse',
    route: '/plano-saude',
    description: 'Conciliação de planos.',
    isActive: true,
    category: 'Saúde'
  },
  {
    id: 'mod-viagens',
    name: 'Despesas de Viagens',
    icon: 'fa-solid fa-plane-departure',
    route: '/despesas-viagens',
    description: 'Relatórios e dashboards',
    isActive: true,
    category: 'Financeiro'
  },
  {
    id: 'mod-extratores',
    name: 'Extratores',
    icon: 'fa-solid fa-file-import',
    route: '/extratores',
    description: 'Importação e processamento.',
    isActive: true,
    category: 'Importação'
  },
  {
    id: 'mod-inadimplencia',
    name: 'Inadimplência',
    icon: 'fa-solid fa-file-invoice-dollar',
    route: '/inadimplencia',
    description: 'Gestão de inadimplência.',
    isActive: true,
    category: 'Cobrança'
  },
  {
    id: 'mod-conciliacao',
    name: 'Conciliação de Pagamentos',
    icon: 'fa-solid fa-scale-balanced',
    route: '/conciliacao-pagamentos',
    description: 'Conciliação de pagamentos.',
    isActive: true,
    category: 'Pagamentos'
  },
  {
    id: 'mod-configuracoes',
    name: 'Configurações e Cadastros',
    icon: 'fa-solid fa-gear',
    route: '/configuracoes-cadastros',
    description: 'Gestão de usuários e acessos.',
    isActive: true,
    category: 'Administrativo'
  }
];
