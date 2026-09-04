import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { IDashboardService } from '../interfaces/dashboard.service';
import { LastAccess, SummaryCard } from '../models/dashboard.model';
import { MOCK_LAST_ACCESSES, MOCK_SUMMARY_CARDS } from '../mock/dashboard.mock';

@Injectable({
  providedIn: 'root'
})
export class MockDashboardService implements IDashboardService {
  getSummaryCards(): Observable<SummaryCard[]> {
    return of(MOCK_SUMMARY_CARDS).pipe(delay(600)); // Simula latência
  }

  getLastAccesses(): Observable<LastAccess[]> {
    return of(MOCK_LAST_ACCESSES).pipe(delay(400));
  }
}
