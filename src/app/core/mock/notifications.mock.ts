import { AppNotification } from '../models/notification.model';

export const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'notif-1',
    title: 'Nova Venda Realizada',
    message: 'O cliente "Empresa ABC" aprovou o orçamento #1024.',
    type: 'success',
    isRead: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 mins atrás
    link: '/crm/sales/1024'
  },
  {
    id: 'notif-2',
    title: 'Estoque Baixo',
    message: 'O produto "Monitor 24pol" atingiu o estoque mínimo de segurança.',
    type: 'warning',
    isRead: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 horas atrás
    link: '/stock/products/33'
  },
  {
    id: 'notif-3',
    title: 'Relatório Mensal',
    message: 'O fechamento do mês de Julho foi gerado com sucesso.',
    type: 'info',
    isRead: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(), // 2 dias atrás
  },
  {
    id: 'notif-4',
    title: 'Falha na Sincronização',
    message: 'Não foi possível sincronizar as notas fiscais com a SEFAZ.',
    type: 'error',
    isRead: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(), // 3 dias atrás
  }
];
