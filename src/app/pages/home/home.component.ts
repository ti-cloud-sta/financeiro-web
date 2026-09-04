import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterModule, Router } from '@angular/router';

import { IAuthService } from '../../core/interfaces/auth.service';
import { IModulesService } from '../../core/interfaces/modules.service';

import { CardComponent } from '../../shared/components/card/card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule, 
    RouterModule,
    CardComponent
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit, OnDestroy {
  authService = inject(IAuthService);
  private modulesService = inject(IModulesService);
  private router = inject(Router);

  user = this.authService.currentUser;
  
  // Real-time clock
  currentDate = new Date();
  private timerId: any;

  // Signal dos módulos
  modules = toSignal(this.modulesService.getActiveModules());

  ngOnInit() {
    if (!this.authService.isAuthenticated() || !this.authService.getToken()) {
      this.router.navigate(['/login']);
      return;
    }

    this.timerId = setInterval(() => {
      this.currentDate = new Date();
    }, 1000);
  }

  ngOnDestroy() {
    if (this.timerId) {
      clearInterval(this.timerId);
    }
  }
}
