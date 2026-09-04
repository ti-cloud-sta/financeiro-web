export interface SummaryCard {
  id: string;
  title: string;
  value: string | number;
  icon: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  colorClass?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
}

export interface LastAccess {
  id: string;
  label: string;
  route: string;
  icon: string;
  timestamp: string;
}
