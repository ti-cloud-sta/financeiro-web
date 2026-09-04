import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of, map } from 'rxjs';
import { Router } from '@angular/router';
import { IAuthService } from '../interfaces/auth.service';
import { AuthResponse, AuthTokens, LoginCredentials } from '../models/auth.model';
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
  private readonly REFRESH_TOKEN_KEY = 'erp_refresh_token';

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
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  private setRefreshToken(token: string): void {
    localStorage.setItem(this.REFRESH_TOKEN_KEY, token);
  }

  login(credentials: LoginCredentials): Observable<AuthResponse> {
    return this.http.post<any>(`${this.API_URL}/auth/login`, credentials).pipe(
      map(response => {
        const tokens: AuthTokens = {
          accessToken: response.access_token,
          refreshToken: '', 
          expiresIn: response.expires_in
        };
        
        const user: User = {
          id: response.email,
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
        if (authResponse.tokens.refreshToken) {
          this.setRefreshToken(authResponse.tokens.refreshToken);
        }
        this._currentUser.set(authResponse.user);
        localStorage.setItem(this.USER_STORAGE_KEY, JSON.stringify(authResponse.user));
      })
    );
  }

  logout(): Observable<void> {
    this.clearSession();
    this.router.navigate(['/login']);
    return of(undefined);
  }

  refreshToken(refreshToken: string): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${this.API_URL}/auth/refresh`, { refreshToken }).pipe(
      tap(tokens => {
        this.setToken(tokens.accessToken);
        if (tokens.refreshToken) {
          this.setRefreshToken(tokens.refreshToken);
        }
      })
    );
  }
}
