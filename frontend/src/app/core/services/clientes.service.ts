import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Cliente {
  idclientes: number;
  codigo: number;
  nome: string;
  linked: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ClientesService {
  private apiUrl = `${environment.apiUrl}/clientes`;

  constructor(private http: HttpClient) { }

  listar(idRepresentante?: number): Observable<Cliente[]> {
    let params = new HttpParams();
    if (idRepresentante) {
      params = params.set('id_representante', idRepresentante.toString());
    }
    return this.http.get<Cliente[]>(this.apiUrl, { params });
  }

  vincularRepresentante(idRepresentante: number, idsClientes: number[]): Observable<any> {
    return this.http.post(`${this.apiUrl}/representante/${idRepresentante}/vincular`, { ids_clientes: idsClientes });
  }
}
