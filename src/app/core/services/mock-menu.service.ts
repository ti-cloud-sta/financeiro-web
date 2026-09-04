import { Injectable, inject } from '@angular/core';
import { Observable, delay, map, switchMap, of } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { IMenuService } from '../interfaces/menu.service';
import { MenuItem } from '../models/menu.model';
import { MOCK_MENU } from '../mock/menu.mock';
import { IPermissionsService } from '../interfaces/permissions.service';
import { IAuthService } from '../interfaces/auth.service';

@Injectable({
  providedIn: 'root'
})
export class MockMenuService implements IMenuService {
  private permissionsService = inject(IPermissionsService);
  private authService = inject(IAuthService);

  getMenu(): Observable<MenuItem[]> {
    // Transformar o signal em observable para reagir dinamicamente às trocas de sessão sem refresh
    return toObservable(this.authService.currentUser).pipe(
      switchMap(user => {
        if (!user) {
          return of([]).pipe(delay(200));
        }

        return this.permissionsService.getUserPermissions(user.id).pipe(
          delay(300),
          map(permissions => {
            const userPermCodes = permissions.map(p => p.code);
            
            // Regra especial: se o mock de permissões estiver sempre retornando todas as permissões (MOCK_PERMISSIONS),
            // a role do usuário não seria avaliada. Para o menu Configurações, vamos verificar explicitamente a role admin.
            const filterMenu = (items: MenuItem[]): MenuItem[] => {
              return items
                .filter(item => {
                  if (item.requiredPermissions?.includes('users:read') && user.role !== 'admin') {
                    return false;
                  }
                  
                  if (!item.requiredPermissions || item.requiredPermissions.length === 0) {
                    return true;
                  }
                  // O usuário precisa ter pelo menos uma das permissões requisitadas (OR)
                  return item.requiredPermissions.some(req => userPermCodes.includes(req));
                })
                .map(item => {
                  if (item.children) {
                    return { ...item, children: filterMenu(item.children) };
                  }
                  return item;
                })
                .sort((a, b) => a.order - b.order);
            };

            return filterMenu(MOCK_MENU);
          })
        );
      })
    );
  }
}
