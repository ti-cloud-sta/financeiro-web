import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AtualizacaoHistoryItem, ContaPagarItem, MatrizCardItem } from '../../pages/previsao-caixa/previsao-caixa.mock';

export interface ImportacaoApbResult {
  sucesso: boolean;
  mensagem: string;
  idImportacoes: number;
  nomeArquivo: string;
  totalRegistros: number;
  totalValor: number;
}

export type ImportacaoAcrResult = ImportacaoApbResult;
export type ImportacaoTitulosLiquidadosResult = ImportacaoApbResult;

export interface DashboardVisaoGeral {
  data_referencia: string;
  data_formatada: string;
  is_hoje: boolean;

  total_provisao: number;
  qtd_provisoes: number;
  total_pagar: number;
  qtd_pagar_real: number;
  total_bb: number;
  total_itau: number;

  contas_bb: ContaPagarItem[];
  contas_itau: ContaPagarItem[];
  contas_provisao: ContaPagarItem[];
  matrizes_agrupadas?: MatrizCardItem[];

  total_receber: number;
  qtd_receber: number;
  total_receber_carteira: number;
  total_receber_boleto: number;
  receber_menor_igual_80: number;
  receber_maior_80: number;
  saldo_previsibilidade: number;
  saldo_real_nominal: number;
  valor_investido_resgatavel: number;
  contas_receber: any[];
}

@Injectable({
  providedIn: 'root'
})
export class PrevisaoCaixaService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/previsao-caixa`;

  /**
   * Realiza o upload e processamento do arquivo APB no backend
   */
  importarApb(file: File): Observable<ImportacaoApbResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<ImportacaoApbResult>(`${this.apiUrl}/importar-apb`, formData);
  }

  /**
   * Realiza o upload e processamento do arquivo ACR no backend
   */
  importarAcr(file: File): Observable<ImportacaoAcrResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<ImportacaoAcrResult>(`${this.apiUrl}/importar-acr`, formData);
  }

  /**
   * Realiza o upload e processamento do arquivo de Títulos Liquidados no backend
   */
  importarTitulosLiquidados(file: File): Observable<ImportacaoTitulosLiquidadosResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<ImportacaoTitulosLiquidadosResult>(`${this.apiUrl}/importar-titulos-liquidados`, formData);
  }

  /**
   * Obtém o histórico de importações do tipo Previsão de Caixa / APB
   */
  listarImportacoes(tipo?: string): Observable<AtualizacaoHistoryItem[]> {
    let params = new HttpParams();
    if (tipo) {
      params = params.set('tipo', tipo);
    }
    return this.http.get<AtualizacaoHistoryItem[]>(`${this.apiUrl}/importacoes`, { params });
  }

  /**
   * Exclui uma importação e seus registros associados em cascata
   */
  excluirImportacao(idImportacoes: number): Observable<{ sucesso: boolean; mensagem: string }> {
    return this.http.delete<{ sucesso: boolean; mensagem: string }>(`${this.apiUrl}/importacoes/${idImportacoes}`);
  }

  /**
   * Obtém os dados consolidados do painel Visão Geral
   */
  obterVisaoGeral(data?: string): Observable<DashboardVisaoGeral> {
    let params = new HttpParams();
    if (data) {
      params = params.set('data', data);
    }
    return this.http.get<DashboardVisaoGeral>(`${this.apiUrl}/visao-geral`, { params });
  }
}
