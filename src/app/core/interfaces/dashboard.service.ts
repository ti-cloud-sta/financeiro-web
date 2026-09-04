import { Observable } from 'rxjs';
import { LastAccess, SummaryCard } from '../models/dashboard.model';

export abstract class IDashboardService {
  abstract getSummaryCards(): Observable<SummaryCard[]>;
  abstract getLastAccesses(): Observable<LastAccess[]>;
}
