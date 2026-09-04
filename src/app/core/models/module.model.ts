export interface AppModule {
  id: string;
  name: string;
  icon: string;
  route: string;
  description: string;
  isActive: boolean;
  category?: string;
}
