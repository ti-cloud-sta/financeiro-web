import { Observable } from 'rxjs';
import { Permission } from '../models/permission.model';

export abstract class IPermissionsService {
  abstract getUserPermissions(userId: string): Observable<Permission[]>;
  abstract hasPermission(userId: string, code: string): Observable<boolean>;
  abstract getAllPermissions(): Observable<Permission[]>;
}
