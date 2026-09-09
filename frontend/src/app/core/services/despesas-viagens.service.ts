import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface DespesaParaSalvar {
  empresa: string;
  colaborador: string;
  colaborador_original?: string;
  categoria: string;
  categoria_original?: string;
  valor: number;
  data?: string;
  nroDocumento?: string;
}

export interface ConfirmarDespesasPayload {
  nomeArquivo: string;
  despesas: DespesaParaSalvar[];
  idUserInc?: number;
  dataCompetencia?: string;
  isManualEntry?: boolean;
  idEmpresaManual?: number;
}

export interface FiltrosDashboard {
  data_inicio?: string;
  data_fim?: string;
  id_empresa?: number;
  id_colaborador?: number;
  id_categoria?: number;
}

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
    return this.http.post(`${this.apiUrl}/analisar-arquivo`, formData);
  }

  confirmarDespesas(payload: ConfirmarDespesasPayload): Observable<any> {
    return this.http.post(`${this.apiUrl}/confirmar-importacao`, payload);
  }

  obterDashboardVisaoGeral(filtros: FiltrosDashboard): Observable<any> {
    let params = new HttpParams();
    if (filtros.data_inicio) params = params.set('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params = params.set('data_fim', filtros.data_fim);
    if (filtros.id_empresa) params = params.set('id_empresa', filtros.id_empresa.toString());
    if (filtros.id_colaborador) params = params.set('id_colaborador', filtros.id_colaborador.toString());
    if (filtros.id_categoria) params = params.set('id_categoria', filtros.id_categoria.toString());
    return this.http.get<any>(`${this.apiUrl}/dashboard/visao-geral`, { params });
  }

  obterVisaoComercial(filtros: FiltrosDashboard): Observable<any> {
    let params = new HttpParams();
    if (filtros.data_inicio) params = params.set('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params = params.set('data_fim', filtros.data_fim);
    if (filtros.id_empresa) params = params.set('id_empresa', filtros.id_empresa.toString());
    if (filtros.id_colaborador) params = params.set('id_colaborador', filtros.id_colaborador.toString());
    if (filtros.id_categoria) params = params.set('id_categoria', filtros.id_categoria.toString());
    return this.http.get<any>(`${this.apiUrl}/dashboard/comercial`, { params });
  }

  obterRelatorio(filtros: any): Observable<any> {
    let params = new HttpParams();
    if (filtros.data_inicio) params = params.set('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params = params.set('data_fim', filtros.data_fim);
    if (filtros.id_empresa) params = params.set('id_empresa', filtros.id_empresa.toString());
    if (filtros.id_colaborador) params = params.set('id_colaborador', filtros.id_colaborador.toString());
    if (filtros.id_centro_custo) params = params.set('id_centro_custo', filtros.id_centro_custo);
    return this.http.get<any>(`${this.apiUrl}/relatorio`, { params });
  }
}

