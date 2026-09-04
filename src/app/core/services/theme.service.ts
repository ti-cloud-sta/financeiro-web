import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private activeThemeSignal = signal<'light' | 'dark'>('light');
  activeTheme = this.activeThemeSignal.asReadonly();

  constructor() {
    // Read from localStorage (if browser environment)
    if (typeof window !== 'undefined' && window.localStorage) {
      const saved = window.localStorage.getItem('santamaria-theme') as 'light' | 'dark';
      if (saved === 'light' || saved === 'dark') {
        this.setTheme(saved);
      } else {
        // Fallback to system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.setTheme(prefersDark ? 'dark' : 'light');
      }
    }
  }

  setTheme(theme: 'light' | 'dark') {
    this.activeThemeSignal.set(theme);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('santamaria-theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
      document.documentElement.setAttribute('data-bs-theme', theme);
    }
  }

  toggleTheme() {
    this.setTheme(this.activeThemeSignal() === 'light' ? 'dark' : 'light');
  }
}
