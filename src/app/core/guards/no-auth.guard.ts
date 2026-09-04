import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { IAuthService } from '../interfaces/auth.service';

export const noAuthGuard: CanActivateFn = (route, state) => {
  const authService = inject(IAuthService);
  const router = inject(Router);

  // Se já está autenticado, manda pra home
  if (authService.isAuthenticated()) {
    return router.createUrlTree(['/home']);
  }

  // Se não está, permite acessar a rota (ex: login)
  return true;
};
