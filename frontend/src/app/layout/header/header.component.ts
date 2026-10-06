import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { IAuthService } from '../../core/interfaces/auth.service';
import { AvatarComponent } from '../../shared/components/avatar/avatar.component';
import { ThemeService } from '../../core/services/theme.service';
import { isAmbienteTeste } from '../../core/config/ambiente';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, AvatarComponent],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  themeService = inject(ThemeService);
  authService = inject(IAuthService);
  user = this.authService.currentUser;
  readonly isAmbienteTeste = isAmbienteTeste;

  logout() {
    this.authService.logout().subscribe();
  }
}
