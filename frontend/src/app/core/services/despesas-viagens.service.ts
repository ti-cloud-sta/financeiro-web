import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DespesasViagensService {
  private apiUrl = `${environment.apiUrl}/despesas-viagens`;

  constructor(private http: HttpClient) {}

  processarArquivo(file: File, empresaNome: string): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('empresa_nome', empresaNome);
    
    // Calls the existing endpoint on the new isolated backend router
    return this.http.post(`${this.apiUrl}/analisar-arquivo`, formData);
  }
}
