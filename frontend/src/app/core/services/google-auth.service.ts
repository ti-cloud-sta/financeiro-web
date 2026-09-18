import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of, firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface GoogleAuthStatus {
  conectado: boolean;
  email?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class GoogleAuthService {
  private apiUrl = `${environment.apiUrl}/auth/google`;

  readonly isConectado = signal<boolean>(false);
  readonly emailConectado = signal<string | null>(null);
  readonly isCarregando = signal<boolean>(false);

  constructor(private http: HttpClient) {}

  /**
   * Consulta o backend para checar se o usuário atual possui token de autorização do Google.
   */
  verificarStatus(): Observable<GoogleAuthStatus> {
    this.isCarregando.set(true);
    return this.http.get<GoogleAuthStatus>(`${this.apiUrl}/status`).pipe(
      tap(status => {
        this.isConectado.set(status.conectado);
        this.emailConectado.set(status.email || null);
        this.isCarregando.set(false);
      }),
      catchError(err => {
        console.error('Erro ao verificar status da conta Google:', err);
        this.isConectado.set(false);
        this.emailConectado.set(null);
        this.isCarregando.set(false);
        return of({ conectado: false, email: null });
      })
    );
  }

  /**
   * Inicia o fluxo de autorização OAuth abrindo a tela de consentimento do Google em um popup centralizado.
   * Retorna uma Promise que resolve quando a autorização for concluída com sucesso.
   */
  async iniciarAutorizacaoPopup(): Promise<boolean> {
    this.isCarregando.set(true);

    try {
      const resp = await firstValueFrom(this.http.get<{ url: string }>(`${this.apiUrl}/url`));
      if (!resp || !resp.url) {
        throw new Error('Não foi possível obter a URL de autorização do Google.');
      }

      return new Promise<boolean>((resolve, reject) => {
        const width = 520;
        const height = 660;
        const left = Math.max(0, window.screenX + (window.outerWidth - width) / 2);
        const top = Math.max(0, window.screenY + (window.outerHeight - height) / 2);

        const popup = window.open(
          resp.url,
          'google_oauth_popup',
          `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes,scrollbars=yes`
        );

        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
          this.isCarregando.set(false);
          reject(new Error('O popup de autorização foi bloqueado pelo navegador. Por favor, permita popups para este site.'));
          return;
        }

        let timer: any = null;

        const cleanup = () => {
          window.removeEventListener('message', messageHandler);
          if (timer) clearInterval(timer);
          this.isCarregando.set(false);
        };

        const messageHandler = (event: MessageEvent) => {
          if (event.data?.type === 'GOOGLE_AUTH_SUCCESS') {
            this.isConectado.set(true);
            if (event.data.email) {
              this.emailConectado.set(event.data.email);
            }
            cleanup();
            resolve(true);
          } else if (event.data?.type === 'GOOGLE_AUTH_ERROR') {
            cleanup();
            reject(new Error(event.data.detail || 'Falha na autorização do Google.'));
          }
        };

        window.addEventListener('message', messageHandler);

        // Monitorar se a janela foi fechada manualmente pelo usuário sem concluir
        timer = setInterval(() => {
          if (popup.closed) {
            cleanup();
            // Verifica o status no backend por garantia
            this.verificarStatus().subscribe(status => {
              if (status.conectado) {
                resolve(true);
              } else {
                reject(new Error('A janela de autorização do Google foi fechada antes da conclusão.'));
              }
            });
          }
        }, 800);
      });
    } catch (err: any) {
      this.isCarregando.set(false);
      throw err;
    }
  }

  /**
   * Desconecta a conta do Google e revoga o token no backend.
   */
  desconectar(): Observable<any> {
    this.isCarregando.set(true);
    return this.http.post(`${this.apiUrl}/desconectar`, {}).pipe(
      tap(() => {
        this.isConectado.set(false);
        this.emailConectado.set(null);
        this.isCarregando.set(false);
      }),
      catchError(err => {
        this.isCarregando.set(false);
        throw err;
      })
    );
  }
}
