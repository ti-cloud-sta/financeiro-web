import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { IEnvironmentService } from '../http/environment.service';
import { User } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class UsersService {
  private http = inject(HttpClient);
  private envService = inject(IEnvironmentService);
  private readonly API_URL = this.envService.apiUrl;

  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.API_URL}/users`);
  }

  changePassword(userId: string | number, novaSenha: string): Observable<any> {
    return this.http.put(`${this.API_URL}/users/${userId}/password`, { novaSenha });
  }

  changeStatus(userId: string | number, bloqueado: boolean): Observable<any> {
    return this.http.patch(`${this.API_URL}/users/${userId}/status`, { bloqueado });
  }

  grantAdmin(userId: string | number): Observable<any> {
    return this.http.patch(`${this.API_URL}/users/${userId}/admin`, { admin: true });
  }

  register(userData: any): Observable<User> {
    return this.http.post<User>(`${this.API_URL}/auth/register`, userData);
  }
}
