import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from './colaboradores.service';

export interface CargoColaborador {
  idCargoColaborador?: number;
  nome: string;
  descricao?: string;
}

@Injectable({
  providedIn: 'root'
})
export class CargosColaboradoresService {
  private apiUrl = `${environment.apiUrl}/cargos-colaboradores`;

  constructor(private http: HttpClient) {}

  listar(page = 1, pageSize = 100): Observable<PaginatedResponse<CargoColaborador>> {
    return this.http.get<PaginatedResponse<CargoColaborador>>(`${this.apiUrl}?page=${page}&page_size=${pageSize}`);
  }

  criar(cargo: CargoColaborador): Observable<CargoColaborador> {
    return this.http.post<CargoColaborador>(this.apiUrl, cargo);
  }

  atualizar(id: number, cargo: CargoColaborador): Observable<CargoColaborador> {
    return this.http.put<CargoColaborador>(`${this.apiUrl}/${id}`, cargo);
  }

  excluir(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}
