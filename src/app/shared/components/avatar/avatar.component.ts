import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-avatar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './avatar.component.html',
  styleUrl: './avatar.component.scss'
})
export class AvatarComponent {
  @Input() imageUrl?: string;
  @Input() initials?: string;
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() status?: 'online' | 'offline';
}
