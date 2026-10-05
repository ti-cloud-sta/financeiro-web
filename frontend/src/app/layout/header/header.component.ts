import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { IAuthService } from '../../core/interfaces/auth.service';
import { AvatarComponent } from '../../shared/components/avatar/avatar.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { ThemeService } from '../../core/services/theme.service';
import { AmbienteApiService } from '../../core/services/ambiente-api.service';
import { AmbienteApi } from '../../core/config/ambiente-api';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, AvatarComponent, ConfirmModalComponent],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  themeService = inject(ThemeService);
  authService = inject(IAuthService);
  ambienteApi = inject(AmbienteApiService);
  user = this.authService.currentUser;
  isAdmin = computed(() => this.user()?.role === 'admin');

  ambienteDestino = signal<AmbienteApi | null>(null);
  mensagemTrocaAmbiente = computed(() =>
    this.ambienteDestino() === 'dev'
      ? 'Você vai usar a API e o banco de DEV (cópia da produção atualizada toda sexta). Alterações feitas lá não afetam a produção.\n\nSua sessão será encerrada e será preciso entrar novamente.'
      : 'Você vai voltar para a API e o banco de PRODUÇÃO.\n\nSua sessão será encerrada e será preciso entrar novamente.'
  );

  logout() {
    this.authService.logout().subscribe();
  }

  solicitarTrocaAmbiente(destino: AmbienteApi) {
    if (destino !== this.ambienteApi.ambiente) {
      this.ambienteDestino.set(destino);
    }
  }

  confirmarTrocaAmbiente() {
    const destino = this.ambienteDestino();
    if (destino) {
      this.ambienteApi.trocarAmbiente(destino);
    }
  }
}
