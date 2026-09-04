import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { IModulesService } from '../interfaces/modules.service';
import { AppModule } from '../models/module.model';
import { MOCK_MODULES } from '../mock/modules.mock';

@Injectable({
  providedIn: 'root'
})
export class MockModulesService implements IModulesService {
  getAvailableModules(): Observable<AppModule[]> {
    return of(MOCK_MODULES).pipe(delay(400));
  }

  getActiveModules(): Observable<AppModule[]> {
    const active = MOCK_MODULES.filter(m => m.isActive);
    return of(active).pipe(delay(300));
  }
}
