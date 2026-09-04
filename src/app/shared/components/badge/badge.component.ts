import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-badge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './badge.component.html',
  styleUrl: './badge.component.scss'
})
export class BadgeComponent {
  @Input() variant: 'success' | 'warning' | 'error' | 'danger' | 'info' | 'primary' | 'secondary' = 'info';
  @Input() text = '';

  getBadgeClass(): string {
    const bsVariant = this.variant === 'error' ? 'danger' : this.variant;
    return `badge bg-${bsVariant}-subtle text-${bsVariant} rounded-pill fw-medium`;
  }
}
