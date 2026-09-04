import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Unidade {
  idUnidade?: number;
  codigo: number;
  descricao: string;
}

export interface UnidadePaginatedResponse {
  items: Unidade[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

@Injectable({
  providedIn: 'root'
})
export class UnidadesService {
  private apiUrl = `${environment.apiUrl}/unidades`;

  constructor(private http: HttpClient) {}

  listar(page: number = 1, limit: number = 20, search?: string): Observable<UnidadePaginatedResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', limit.toString());
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<UnidadePaginatedResponse>(this.apiUrl, { params });
  }

  criar(unidade: Unidade): Observable<Unidade> {
    return this.http.post<Unidade>(this.apiUrl, unidade);
  }

  atualizar(id: number, unidade: Unidade): Observable<Unidade> {
    return this.http.put<Unidade>(`${this.apiUrl}/${id}`, unidade);
  }

  excluir(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}
