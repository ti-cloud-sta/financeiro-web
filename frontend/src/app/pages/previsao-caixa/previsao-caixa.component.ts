import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonComponent } from '../../shared/components/button/button.component';

@Component({
  selector: 'app-previsao-caixa',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  templateUrl: './previsao-caixa.component.html',
  styleUrls: ['./previsao-caixa.component.scss']
})
export class PrevisaoCaixaComponent implements OnInit {
  isSidebarCollapsed = false;

  ngOnInit() {
    this.isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
  }

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  abrirModulo() {
    console.log('Módulo de Previsão de Caixa iniciado.');
  }
}
