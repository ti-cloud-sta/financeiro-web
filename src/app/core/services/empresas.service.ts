import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Empresa {
  idEmpresas?: number;
  nome: string;
  descricao?: string;
  createdAt?: string;
  updatedAte?: string;
  icon?: string; // Propriedade extra para o front-end
  modulo_id?: number;
  modulo_ids?: number[];
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

@Injectable({
  providedIn: 'root'
})
export class EmpresasService {
  private apiUrl = `${environment.apiUrl}/empresas`;

  constructor(private http: HttpClient) {}

  listar(page = 1, pageSize = 100, search: string = '', modulo?: number): Observable<PaginatedResponse<Empresa>> {
    let url = `${this.apiUrl}?page=${page}&page_size=${pageSize}`;
    if (search) {
      url += `&q=${encodeURIComponent(search)}`;
    }
    if (modulo) {
      url += `&modulo=${modulo}`;
    }
    return this.http.get<PaginatedResponse<Empresa>>(url);
  }

  buscarPorId(id: number): Observable<Empresa> {
    return this.http.get<Empresa>(`${this.apiUrl}/${id}`);
  }

  criar(empresa: Empresa): Observable<Empresa> {
    return this.http.post<Empresa>(this.apiUrl, empresa);
  }

  atualizar(id: number, empresa: Partial<Empresa>): Observable<Empresa> {
    return this.http.put<Empresa>(`${this.apiUrl}/${id}`, empresa);
  }

  excluir(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
