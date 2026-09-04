import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError, catchError } from 'rxjs';
import { IAuthService } from '../interfaces/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(IAuthService);

  const token = authService.getToken();
  
  let authReq = req;
  if (token) {
    authReq = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${token}`)
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 || error.status === 403) {
        authService.logout().subscribe();
      }
      return throwError(() => error);
    })
  );
};
