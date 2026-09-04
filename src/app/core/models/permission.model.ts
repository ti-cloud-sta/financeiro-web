export interface Permission {
  id: string;
  name: string;
  description: string;
  code: string; // ex: 'users:read', 'sales:create'
}
