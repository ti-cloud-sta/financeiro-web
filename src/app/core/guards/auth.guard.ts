import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { IAuthService } from '../interfaces/auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(IAuthService);
  const router = inject(Router);

  // Verifica se há token e se a sessão está ativa
  if (authService.isAuthenticated() && authService.getToken()) {
    return true;
  }

  // Redireciona para o login guardando URL de retorno
  return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};
