import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { IPermissionsService } from '../interfaces/permissions.service';
import { Permission } from '../models/permission.model';
import { MOCK_PERMISSIONS } from '../mock/permissions.mock';

@Injectable({
  providedIn: 'root'
})
export class MockPermissionsService implements IPermissionsService {
  getUserPermissions(userId: string): Observable<Permission[]> {
    // Retorna todas as permissões para o mock
    return of(MOCK_PERMISSIONS).pipe(delay(300));
  }

  hasPermission(userId: string, code: string): Observable<boolean> {
    const hasPerm = MOCK_PERMISSIONS.some(p => p.code === code);
    return of(hasPerm).pipe(delay(100));
  }

  getAllPermissions(): Observable<Permission[]> {
    return of(MOCK_PERMISSIONS).pipe(delay(300));
  }
}
