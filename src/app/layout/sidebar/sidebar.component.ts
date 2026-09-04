import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { LayoutService } from '../../core/services/layout.service';
import { IMenuService } from '../../core/interfaces/menu.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  layoutService = inject(LayoutService);
  menuService = inject(IMenuService);
  
  isCollapsed = this.layoutService.isSidebarCollapsed;
  menuItems = toSignal(this.menuService.getMenu(), { initialValue: [] });
  
  // Rastreia quais menus com filhos estão abertos (id do menu)
  expandedMenus = signal<Set<string>>(new Set());

  toggleSubmenu(menuId: string) {
    if (this.isCollapsed()) return; // não expande submenu se a sidebar estiver fechada

    this.expandedMenus.update(set => {
      const newSet = new Set(set);
      if (newSet.has(menuId)) {
        newSet.delete(menuId);
      } else {
        newSet.add(menuId);
      }
      return newSet;
    });
  }

  isExpanded(menuId: string): boolean {
    return this.expandedMenus().has(menuId);
  }
}
