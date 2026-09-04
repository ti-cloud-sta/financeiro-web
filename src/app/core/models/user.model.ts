export interface User {
  id: string;
  iduser?: number;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'manager';
  avatarUrl?: string;
  active?: 'S' | 'N';
  createdAt?: string;
}
