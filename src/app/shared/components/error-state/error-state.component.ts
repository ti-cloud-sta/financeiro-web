import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-error-state',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  templateUrl: './error-state.component.html',
  styleUrl: './error-state.component.scss'
})
export class ErrorStateComponent {
  @Input() title = 'Ocorreu um erro';
  @Input() message = 'Não foi possível carregar as informações. Tente novamente mais tarde.';
  @Input() retryable = true;

  @Output() retry = new EventEmitter<void>();

  onRetry() {
    this.retry.emit();
  }
}
