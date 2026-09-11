import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './modal.component.html',
  styleUrl: './modal.component.scss'
})
export class ModalComponent {
  @Input() isOpen = false;
  @Input() title = '';
  @Input() size: 'sm' | 'md' | 'lg' | 'xl' = 'md';
  @Input() fixedHeight = false;
  @Input() customBodyStyle: any = null;

  @Output() closed = new EventEmitter<string | undefined>();

  close(reason?: string) {
    this.isOpen = false;
    this.closed.emit(reason);
  }
}
