import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { IUserService } from '../interfaces/user.service';
import { User } from '../models/user.model';
import { IEnvironmentService } from '../http/environment.service';

@Injectable({
  providedIn: 'root'
})
export class UserService implements IUserService {
  private http = inject(HttpClient);
  private envService = inject(IEnvironmentService);
  private readonly API_URL = this.envService.apiUrl;

  getUserProfile(): Observable<User> {
    return this.http.get<any>(`${this.API_URL}/auth/me`).pipe(
      map(response => ({
        id: response.id?.toString() || response.email,
        email: response.email,
        name: response.name,
        role: response.role || 'user',
        createdAt: response.createdAt
      }))
    );
  }

  updateProfile(user: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.API_URL}/auth/me`, user);
  }
}
