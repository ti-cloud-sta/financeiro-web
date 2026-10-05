import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AMBIENTE_API_STORAGE_KEY, AmbienteApi } from '../config/ambiente-api';
import { IAuthService } from '../interfaces/auth.service';

@Injectable({
  providedIn: 'root'
})
export class AmbienteApiService {
  private authService = inject(IAuthService);

  // Fixo durante a vida da página: trocar de ambiente recarrega a aplicação.
  readonly ambiente: AmbienteApi = environment.ambienteApi;
  readonly isDev = this.ambiente === 'dev';

  /**
   * Os tokens são assinados com chaves diferentes em cada ambiente, então a troca
   * encerra a sessão e recarrega a página para os serviços usarem a nova URL.
   */
  trocarAmbiente(destino: AmbienteApi): void {
    try {
      if (destino === 'dev') {
        localStorage.setItem(AMBIENTE_API_STORAGE_KEY, 'dev');
      } else {
        localStorage.removeItem(AMBIENTE_API_STORAGE_KEY);
      }
    } catch {
      return;
    }

    sessionStorage.removeItem('despesas_viagens_draft');
    this.authService.logout().subscribe();
    window.location.assign('/login');
  }
}
