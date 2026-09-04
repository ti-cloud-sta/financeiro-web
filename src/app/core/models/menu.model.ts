export interface MenuItem {
  id: string;
  label: string;
  icon?: string;
  route?: string;
  children?: MenuItem[];
  isFavorite?: boolean;
  order: number;
  requiredPermissions?: string[]; // Ex: ['sales:read', 'finance:full']
}
