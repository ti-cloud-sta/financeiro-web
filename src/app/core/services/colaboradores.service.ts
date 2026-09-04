import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { CargoColaborador } from './cargos-colaboradores.service';
import { CentroCusto } from './centros-custo.service';
import { Unidade } from './unidades.service';

export interface Colaborador {
  idColaborador?: number;
  nome: string;
  idCentroCusto: number;
  idCargoColaborador: number;
  documento?: string;
  snAtivo?: string;
  unidadeIds?: number[];
  papel?: string;
  cargo_colaborador?: CargoColaborador;
  centro_custo?: CentroCusto;
  unidades?: Unidade[];
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ImportUnidade {
  idUnidade: number;
  codigo: number;
  descricao: string;
}

export interface ImportNovo {
  documento: string;
  nome: string;
  unidades: ImportUnidade[];
  centroCustoCodigo: number;
  idCentroCusto: number | null;
  centroCustoNome: string | null;
  ccEncontrado: boolean;
}

export interface ImportDivergente {
  idColaborador: number;
  documento: string;
  nome: string;
  unidades: ImportUnidade[];
  unidadesAtuais: ImportUnidade[];
  centroCustoCodigo: number;
  idCentroCusto: number | null;
  centroCustoNome: string | null;
  ccEncontrado: boolean;
  idCentroCustoAtual: number;
  centroCustoAtualNome: string | null;
  ccDivergente: boolean;
  unidadesDivergentes: boolean;
  reativado: boolean;
}

export interface ImportDesligado {
  idColaborador: number;
  documento: string;
  nome: string;
  unidadesAtuais: ImportUnidade[];
  centroCustoAtualNome: string | null;
}

export interface ImportErro {
  aba: string;
  linha: number;
  nome: string | null;
  documento: string | null;
  motivo: string;
}

export interface ImportPreviewResponse {
  novos: ImportNovo[];
  divergentes: ImportDivergente[];
  desligados: ImportDesligado[];
  erros: ImportErro[];
}

export interface ImportProcessarResponse {
  cadastrados: number;
  atualizados: number;
  desligados: number;
}

@Injectable({
  providedIn: 'root'
})
export class ColaboradoresService {
  private apiUrl = `${environment.apiUrl}/colaboradores`;

  constructor(private http: HttpClient) {}

  getApiUrl(): string {
    return this.apiUrl;
  }

  listar(page = 1, pageSize = 10, search: string = ''): Observable<PaginatedResponse<Colaborador>> {
    let url = `${this.apiUrl}?page=${page}&page_size=${pageSize}`;
    if (search) {
      url += `&q=${encodeURIComponent(search)}`;
    }
    return this.http.get<PaginatedResponse<Colaborador>>(url);
  }

  buscarPorId(id: number): Observable<Colaborador> {
    return this.http.get<Colaborador>(`${this.apiUrl}/${id}`);
  }

  criar(colaborador: Colaborador): Observable<Colaborador> {
    return this.http.post<Colaborador>(this.apiUrl, colaborador);
  }

  atualizar(id: number, colaborador: Partial<Colaborador>): Observable<Colaborador> {
    return this.http.put<Colaborador>(`${this.apiUrl}/${id}`, colaborador);
  }

  excluir(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  importarPreview(file: File): Observable<ImportPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportPreviewResponse>(`${this.apiUrl}/importar/preview`, formData);
  }

  importarProcessar(payload: {
    novos: { documento: string; nome: string; idCentroCusto: number; unidadeIds: number[] }[];
    divergentes: { idColaborador: number; idCentroCusto: number; unidadeIds: number[] }[];
    desligados: { idColaborador: number }[];
  }): Observable<ImportProcessarResponse> {
    return this.http.post<ImportProcessarResponse>(`${this.apiUrl}/importar/processar`, payload);
  }
}
