import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface RelatorioGeralRow {
  competencia: string;
  unidade?: string;
  empresa?: string;
  nome?: string;
  centro_custo?: string;
  total: number;
}

export interface RelatorioGeralResponse {
  items: RelatorioGeralRow[];
  total: number;
  total_valor: number;
  page: number;
  size: number;
}

export interface ConciliacaoRow {
  unidade_codigo: string;
  unidade_descricao: string;
  empresa_abrev: string;
  total_planilha: number;
  total_sistema: number;
  diferenca: number;
  status: 'OK' | 'DIVERGENTE' | 'NAO_ENCONTRADO_SISTEMA' | 'NAO_ENCONTRADO_PLANILHA';
}

export interface ConciliacaoResponse {
  competencia: string;
  linhas: ConciliacaoRow[];
  total_divergencias: number;
  total_processado: number;
}

@Injectable({
  providedIn: 'root'
})
export class PlanoSaudeService {
  private apiUrl = `${environment.apiUrl}/plano-saude`;

  constructor(private http: HttpClient) {}

  getRelatorioGeral(mes: number, ano: number, search?: string, idEmpresa?: number, page: number = 1, size: number = 10): Observable<RelatorioGeralResponse> {
    let params = new HttpParams()
      .set('mes', mes.toString())
      .set('ano', ano.toString())
      .set('page', page.toString())
      .set('size', size.toString());

    if (search) {
      params = params.set('search', search);
    }
    if (idEmpresa) {
      params = params.set('id_empresa', idEmpresa.toString());
    }

    return this.http.get<RelatorioGeralResponse>(`${this.apiUrl}/relatorio-geral`, { params });
  }

  exportarRelatorioGeral(mes: number, ano: number, search?: string, idEmpresa?: number): Observable<Blob> {
    let params = new HttpParams()
      .set('mes', mes.toString())
      .set('ano', ano.toString());

    if (search) {
      params = params.set('search', search);
    }
    if (idEmpresa) {
      params = params.set('id_empresa', idEmpresa.toString());
    }

    return this.http.get(`${this.apiUrl}/relatorio-geral/exportar`, {
      params,
      responseType: 'blob'
    });
  }

  conciliarPlanilha(file: File): Observable<ConciliacaoResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ConciliacaoResponse>(`${this.apiUrl}/relatorio-geral/conciliar`, formData);
  }
}
