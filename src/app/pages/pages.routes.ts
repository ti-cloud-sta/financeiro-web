import { Routes } from '@angular/router';

export const pagesRoutes: Routes = [
  {
    path: '',
    redirectTo: 'home',
    pathMatch: 'full'
  },
  { 
    path: 'home', 
    loadComponent: () => import('./home/home.component').then(m => m.HomeComponent),
    data: { breadcrumb: 'Home' }
  },
  {
    path: 'plano-saude',
    loadComponent: () => import('./plano-saude/plano-saude.component').then(m => m.PlanoSaudeComponent),
    data: { breadcrumb: 'Plano de Saúde' }
  },
  {
    path: 'despesas-viagens',
    loadComponent: () => import('./despesas-viagens/despesas-viagens.component').then(m => m.DespesasViagensComponent),
    data: { breadcrumb: 'Despesas de Viagens', icon: 'fa-solid fa-plane-departure' }
  },
  {
    path: 'extratores',
    loadComponent: () => import('./extratores/extratores.component').then(m => m.ExtratoresComponent),
    data: { breadcrumb: 'Extratores', icon: 'fa-solid fa-file-import' }
  },
  {
    path: 'inadimplencia',
    loadComponent: () => import('./inadimplencia/inadimplencia.component').then(m => m.InadimplenciaComponent),
    data: { breadcrumb: 'Inadimplência', icon: 'fa-solid fa-file-invoice-dollar' }
  },
  {
    path: 'conciliacao-pagamentos',
    loadComponent: () => import('./conciliacao-pagamentos/conciliacao-pagamentos.component').then(m => m.ConciliacaoPagamentosComponent),
    data: { breadcrumb: 'Conciliação de Pagamentos', icon: 'fa-solid fa-scale-balanced' }
  },
  {
    path: 'configuracoes-cadastros',
    loadComponent: () => import('./configuracoes-cadastros/configuracoes-cadastros.component').then(m => m.ConfiguracoesCadastrosComponent),
    data: { breadcrumb: 'Configurações e Cadastros' }
  }
];


