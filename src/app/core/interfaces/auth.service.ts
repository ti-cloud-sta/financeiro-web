import { Observable } from 'rxjs';
import { Signal } from '@angular/core';
import { AuthResponse, AuthTokens, LoginCredentials } from '../models/auth.model';
import { User } from '../models/user.model';

export abstract class IAuthService {
  abstract currentUser: Signal<User | null>;
  abstract isAuthenticated: Signal<boolean>;
  abstract getToken(): string | null;
  abstract getRefreshToken(): string | null;
  
  abstract login(credentials: LoginCredentials): Observable<AuthResponse>;
  abstract logout(): Observable<void>;
  abstract refreshToken(refreshToken: string): Observable<AuthTokens>;
}
