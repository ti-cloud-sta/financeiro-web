import { Permission } from '../models/permission.model';

export const MOCK_PERMISSIONS: Permission[] = [
  { id: 'perm-1', name: 'Ler Usuários', description: 'Permite visualizar a lista de usuários', code: 'users:read' },
  { id: 'perm-2', name: 'Criar Usuários', description: 'Permite cadastrar novos usuários', code: 'users:create' },
  { id: 'perm-3', name: 'Editar Usuários', description: 'Permite alterar dados de usuários', code: 'users:update' },
  { id: 'perm-4', name: 'Excluir Usuários', description: 'Permite remover usuários do sistema', code: 'users:delete' },
  
  { id: 'perm-5', name: 'Ler Vendas', description: 'Visualizar registros de vendas', code: 'sales:read' },
  { id: 'perm-6', name: 'Criar Vendas', description: 'Registrar novas vendas', code: 'sales:create' },
  
  { id: 'perm-7', name: 'Acesso Financeiro', description: 'Acesso total ao módulo financeiro', code: 'finance:full' }
];
