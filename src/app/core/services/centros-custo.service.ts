import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from './colaboradores.service';

export interface CentroCusto {
  idCentroCusto?: number;
  codigo: number;
  nome?: string;
  estados: string[];
}

@Injectable({
  providedIn: 'root'
})
export class CentrosCustoService {
  private apiUrl = `${environment.apiUrl}/centros-custo`;

  constructor(private http: HttpClient) {}

  listar(page = 1, pageSize = 100, search?: string): Observable<PaginatedResponse<CentroCusto>> {
    let url = `${this.apiUrl}?page=${page}&page_size=${pageSize}`;
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }
    return this.http.get<PaginatedResponse<CentroCusto>>(url);
  }

  criar(centro: CentroCusto): Observable<CentroCusto> {
    return this.http.post<CentroCusto>(this.apiUrl, centro);
  }

  atualizar(id: number, centro: CentroCusto): Observable<CentroCusto> {
    return this.http.put<CentroCusto>(`${this.apiUrl}/${id}`, centro);
  }

  excluir(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}
