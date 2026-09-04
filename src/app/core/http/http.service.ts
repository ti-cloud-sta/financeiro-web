import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { catchError, retry, timeout } from 'rxjs/operators';
import { IEnvironmentService } from './environment.service';
import { ApiError } from '../models/api-error.model';

export interface RequestOptions {
  headers?: HttpHeaders | { [header: string]: string | string[] };
  params?: HttpParams | { [param: string]: string | number | boolean | ReadonlyArray<string | number | boolean> };
}

@Injectable({
  providedIn: 'root'
})
export class HttpService {
  private http = inject(HttpClient);
  private env = inject(IEnvironmentService);

  get<T>(endpoint: string, options?: RequestOptions): Observable<T> {
    return this.http.get<T>(`${this.env.apiUrl}${endpoint}`, options).pipe(
      timeout(this.env.defaultTimeout),
      retry({ count: this.env.maxRetries, delay: this.shouldRetry }),
      catchError(this.handleError)
    );
  }

  post<T>(endpoint: string, body: any, options?: RequestOptions): Observable<T> {
    return this.http.post<T>(`${this.env.apiUrl}${endpoint}`, body, options).pipe(
      timeout(this.env.defaultTimeout),
      retry({ count: this.env.maxRetries, delay: this.shouldRetry }),
      catchError(this.handleError)
    );
  }

  put<T>(endpoint: string, body: any, options?: RequestOptions): Observable<T> {
    return this.http.put<T>(`${this.env.apiUrl}${endpoint}`, body, options).pipe(
      timeout(this.env.defaultTimeout),
      retry({ count: this.env.maxRetries, delay: this.shouldRetry }),
      catchError(this.handleError)
    );
  }

  delete<T>(endpoint: string, options?: RequestOptions): Observable<T> {
    return this.http.delete<T>(`${this.env.apiUrl}${endpoint}`, options).pipe(
      timeout(this.env.defaultTimeout),
      retry({ count: this.env.maxRetries, delay: this.shouldRetry }),
      catchError(this.handleError)
    );
  }

  // Lógica de Retry: não tenta de novo se for 400 (Bad Request) ou 401/403 (Auth)
  private shouldRetry = (error: HttpErrorResponse, retryCount: number): Observable<number> => {
    if (error.status === 400 || error.status === 401 || error.status === 403 || error.status === 404) {
      return throwError(() => error);
    }
    // Exponential backoff (1s, 2s, 4s...)
    return timer(Math.pow(2, retryCount) * 1000);
  }

  // Padronização do formato de Erro da API
  private handleError = (error: HttpErrorResponse): Observable<never> => {
    let apiError: ApiError = {
      status: error.status || 500,
      message: 'Ocorreu um erro inesperado no servidor.'
    };

    if (error.error instanceof ErrorEvent) {
      // Erro no lado do cliente (rede, CORS, etc)
      apiError.message = `Erro de rede: ${error.error.message}`;
    } else {
      // Erro vindo do backend
      if (error.error && error.error.message) {
        apiError.message = error.error.message;
        apiError.code = error.error.code;
        apiError.details = error.error.details;
      } else if (error.status === 401) {
        apiError.message = 'Sessão expirada ou não autorizada.';
      } else if (error.status === 403) {
        apiError.message = 'Você não tem permissão para realizar esta ação.';
      } else if (error.status === 404) {
        apiError.message = 'Recurso não encontrado.';
      } else if (error.status === 0) {
        apiError.message = 'Falha de conexão. O servidor pode estar offline.';
      }
    }

    console.error('API Error:', apiError);
    return throwError(() => apiError);
  }
}
