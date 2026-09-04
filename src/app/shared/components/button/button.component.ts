import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './button.component.html',
  styleUrl: './button.component.scss'
})
export class ButtonComponent {
  @Input() variant: 'primary' | 'secondary' | 'danger' | 'ghost' | 'success' | 'warning' | 'outline-success' = 'primary';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() icon?: string;

  @Output() clicked = new EventEmitter<Event>();

  getButtonClasses(): string[] {
    const classes = [];
    
    if (this.variant === 'ghost') {
      classes.push('btn-link', 'text-decoration-none');
    } else {
      classes.push(`btn-${this.variant}`);
    }

    if (this.size !== 'md') {
      classes.push(`btn-${this.size}`);
    }

    return classes;
  }

  onClick(event: Event) {
    if (!this.disabled && !this.loading) {
      this.clicked.emit(event);
    }
  }
}
