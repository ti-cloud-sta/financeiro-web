import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of, map } from 'rxjs';
import { Router } from '@angular/router';
import { IAuthService } from '../interfaces/auth.service';
import { AuthResponse, AuthTokens, LoginCredentials, RegisterCredentials } from '../models/auth.model';
import { IEnvironmentService } from '../http/environment.service';
import { User } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService implements IAuthService {
  private http = inject(HttpClient);
  private envService = inject(IEnvironmentService);
  private router = inject(Router);

  private readonly API_URL = this.envService.apiUrl;
  private readonly USER_STORAGE_KEY = 'erp_current_user';
  private readonly TOKEN_KEY = 'erp_access_token';

  private _currentUser = signal<User | null>(null);

  currentUser = computed(() => this._currentUser());
  isAuthenticated = computed(() => this._currentUser() !== null);

  constructor() {
    this.restoreSession();
  }

  private restoreSession(): void {
    const savedUser = localStorage.getItem(this.USER_STORAGE_KEY);
    if (savedUser) {
      try {
        this._currentUser.set(JSON.parse(savedUser));
      } catch (e) {
        console.error('Failed to parse saved user session', e);
        this.clearSession();
      }
    }
  }

  private clearSession(): void {
    this._currentUser.set(null);
    localStorage.removeItem(this.USER_STORAGE_KEY);
    localStorage.removeItem(this.TOKEN_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  login(credentials: LoginCredentials): Observable<AuthResponse> {
    return this.http.post<any>(`${this.API_URL}/auth/login`, credentials).pipe(
      map(response => {
        const tokens: AuthTokens = {
          accessToken: response.access_token,
          expiresIn: response.expires_in
        };

        const user: User = {
          id: response.email,
          iduser: response.iduser,
          email: response.email,
          name: response.name,
          role: response.role || 'user',
          createdAt: response.createdAt
        };
        
        return { user, tokens };
      }),
      tap((authResponse: AuthResponse) => {
        // Unifica atualização de token, user e local storage
        this.setToken(authResponse.tokens.accessToken);
        this._currentUser.set(authResponse.user);
        localStorage.setItem(this.USER_STORAGE_KEY, JSON.stringify(authResponse.user));
      })
    );
  }

  register(credentials: RegisterCredentials): Observable<void> {
    return this.http.post<void>(`${this.API_URL}/auth/register`, credentials);
  }

  logout(): Observable<void> {
    this.clearSession();
    this.router.navigate(['/login']);
    return of(undefined);
  }
}
