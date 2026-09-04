import { Component, inject, signal, OnInit } from '@angular/core';
import { Router, NavigationEnd, ActivatedRoute, RouterModule } from '@angular/router';
import { filter } from 'rxjs';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-breadcrumb',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './breadcrumb.component.html',
  styleUrl: './breadcrumb.component.scss'
})
export class BreadcrumbComponent implements OnInit {
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);

  currentPageName = signal('Página Atual');
  currentIcon = signal<string | null>(null);

  ngOnInit() {
    this.updateBreadcrumb();
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.updateBreadcrumb();
    });
  }

  private updateBreadcrumb() {
    let route = this.activatedRoute;
    while (route.firstChild) {
      route = route.firstChild;
    }
    const breadcrumbName = route.snapshot.data['breadcrumb'];
    const icon = route.snapshot.data['icon'];
    this.currentIcon.set(icon || null);
    
    if (breadcrumbName) {
      this.currentPageName.set(breadcrumbName);
    } else {
      // Fallback: format route path if no data is provided
      const path = route.snapshot.url.map(segment => segment.path).join('/');
      if (path && path !== '') {
        const formatted = path.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        this.currentPageName.set(formatted);
      } else {
         this.currentPageName.set('Página Atual');
      }
    }
  }
}
