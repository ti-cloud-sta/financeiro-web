import { User } from '../models/user.model';

export const MOCK_USERS: User[] = [
  {
    id: 'usr-1',
    name: 'João Diretor',
    email: 'joao@santamaria.com.br',
    role: 'admin',
    avatarUrl: 'https://i.pravatar.cc/150?u=joao',
    createdAt: '2026-01-15T10:00:00Z'
  },
  {
    id: 'usr-2',
    name: 'Maria Vendedora',
    email: 'maria@santamaria.com.br',
    role: 'user',
    avatarUrl: 'https://i.pravatar.cc/150?u=maria',
    createdAt: '2026-03-22T14:30:00Z'
  },
  {
    id: 'usr-3',
    name: 'Carlos Gerente',
    email: 'carlos@santamaria.com.br',
    role: 'manager',
    createdAt: '2026-05-10T09:15:00Z'
  }
];
