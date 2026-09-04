import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Importacao {
  idImportacoes: number;
  nomeArquivo: string;
  extensaoArquivo: string;
  idEmpresa?: number;
  tipo: string;
  createdAt: string;
  updatedAte?: string;
  empresa?: {
    idEmpresas: number;
    nome: string;
    descricao?: string;
  };
  valor_total?: number;
  autor?: string;
}

export interface ImportacaoPaginatedResponse {
  items: Importacao[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface DespesaExtraida {
  empresa: string;
  colaborador: string;
  categoria: string;
  valor: number;
}

export interface AnaliseExtratoResponse {
  sucesso: boolean;
  dados: DespesaExtraida[];
}

export interface PendenciaKanban {
  idnfpendencias: number;
  titulo: string | null;
  fase: string | null;
  status: string | null;
  clienteNome: string | null;
  dtVencimento: string | null;
  createdAt: string | null;
}

export interface HistoricoApi {
  idhistoricopendencia: number;
  idNfPendencias: number;
  tipo: string | null;
  observacao: string | null;
  createdAt: string | null;
  autor: string | null;
}

export interface TratativaApi {
  idtratativas: number;
  idNfPendencias: number;
  conteudo: string;
  createdAt: string | null;
  autor: string | null;
}

export interface ImportacaoPendenciasResponse {
  sucesso: boolean;
  arquivo: string;
  idImportacao: number;
  totalLinhasComEspecie: number;
  importadas: number;
  classificadasPorFallback: number;
  ignoradasSemCliente: number;
  ignoradasSemVencimento: number;
  ignoradasDuplicadas: number;
  semUnidadeEncontrada: number;
  clientesCriados: number;
  matrizesCriadas: number;
  finalizadasAutomaticamente: number;
  resumoPorFaseStatus: { [key: string]: number };
}

export interface JanelaRegraDia {
  aplicavel: boolean;
  inicio?: string;
  fim?: string;
  diaSemanaHoje: string;
}

@Injectable({
  providedIn: 'root'
})
export class ImportacoesService {
  private apiUrl = `${environment.apiUrl}/importacoes`;

  constructor(private http: HttpClient) {}

  listar(page: number = 1, size: number = 10, search?: string, categoria?: string): Observable<ImportacaoPaginatedResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('size', size.toString());
      
    if (search) {
      params = params.set('search', search);
    }
    if (categoria) {
      params = params.set('categoria', categoria);
    }
    
    return this.http.get<ImportacaoPaginatedResponse>(this.apiUrl, { params });
  }

  listarPendenciasInadimplencia(dataInicio?: string, dataFim?: string): Observable<PendenciaKanban[]> {
    let params = new HttpParams();
    if (dataInicio) params = params.set('data_inicio', dataInicio);
    if (dataFim) params = params.set('data_fim', dataFim);
    return this.http.get<PendenciaKanban[]>(`${this.apiUrl}/inadimplencia/pendencias`, { params });
  }

  obterJanelaRegraDia(): Observable<JanelaRegraDia> {
    return this.http.get<JanelaRegraDia>(`${this.apiUrl}/inadimplencia/janela-regra-dia`);
  }

  alterarFasePendencia(id: number, fase: string): Observable<{ idnfpendencias: number; fase: string }> {
    return this.http.patch<{ idnfpendencias: number; fase: string }>(
      `${this.apiUrl}/inadimplencia/pendencias/${id}/fase`, { fase }
    );
  }

  listarHistoricoPendencia(idNf: number): Observable<HistoricoApi[]> {
    return this.http.get<HistoricoApi[]>(`${this.apiUrl}/inadimplencia/pendencias/${idNf}/historico`);
  }

  listarTratativas(idNf: number): Observable<TratativaApi[]> {
    return this.http.get<TratativaApi[]>(`${this.apiUrl}/inadimplencia/pendencias/${idNf}/tratativas`);
  }

  criarTratativa(idNf: number, conteudo: string): Observable<TratativaApi> {
    return this.http.post<TratativaApi>(`${this.apiUrl}/inadimplencia/pendencias/${idNf}/tratativas`, { conteudo });
  }

  editarTratativa(idTratativa: number, conteudo: string): Observable<TratativaApi> {
    return this.http.put<TratativaApi>(`${this.apiUrl}/inadimplencia/tratativas/${idTratativa}`, { conteudo });
  }

  alterarStatusPendencia(id: number, status: string): Observable<{ idnfpendencias: number; status: string }> {
    return this.http.patch<{ idnfpendencias: number; status: string }>(
      `${this.apiUrl}/inadimplencia/pendencias/${id}/status`, { status }
    );
  }

  importarPendenciasInadimplencia(file: File): Observable<ImportacaoPendenciasResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportacaoPendenciasResponse>(`${this.apiUrl}/inadimplencia/importar-pendencias`, formData);
  }

  analisarExtrato(file: File, empresaNome: string): Observable<AnaliseExtratoResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('empresa_nome', empresaNome);
    
    return this.http.post<AnaliseExtratoResponse>(`${this.apiUrl}/ia/analise-extrato`, formData);
  }

  salvarExtraidos(nomeArquivo: string, despesas: DespesaExtraida[], idUserInc?: number): Observable<any> {
    const payload = {
      nomeArquivo,
      despesas,
      idUserInc
    };
    return this.http.post(`${this.apiUrl}/ia/salvar`, payload);
  }

  excluir(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  obterDadosDashboard(filtros: any): Observable<any> {
    let params = new HttpParams();
    if (filtros.data_inicio) params = params.set('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params = params.set('data_fim', filtros.data_fim);
    if (filtros.id_empresa) params = params.set('id_empresa', filtros.id_empresa.toString());
    if (filtros.id_colaborador) params = params.set('id_colaborador', filtros.id_colaborador.toString());
    if (filtros.id_categoria) params = params.set('id_categoria', filtros.id_categoria.toString());
    if (filtros.tipo_importacao) params = params.set('tipo_importacao', filtros.tipo_importacao);
    
    return this.http.get<any>(`${this.apiUrl}/dashboard`, { params });
  }

  obterDadosDashboardAnalitico(filtros: any): Observable<any> {
    let params = new HttpParams();
    if (filtros.data_inicio) params = params.set('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params = params.set('data_fim', filtros.data_fim);
    if (filtros.id_empresa) params = params.set('id_empresa', filtros.id_empresa.toString());
    if (filtros.id_colaborador) params = params.set('id_colaborador', filtros.id_colaborador.toString());
    if (filtros.id_categoria) params = params.set('id_categoria', filtros.id_categoria.toString());
    if (filtros.tipo_importacao) params = params.set('tipo_importacao', filtros.tipo_importacao);
    
    return this.http.get<any>(`${this.apiUrl}/dashboard/analitico`, { params });
  }

  extrairAtacadao(atacadaoFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('file', atacadaoFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/atacadao/extrair`, formData, {
      responseType: 'blob'
    });
  }

  extrairSendas(sendasFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('file', sendasFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/sendas/extrair`, formData, {
      responseType: 'blob'
    });
  }

  extrairMartMinas(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/martminas/extrair`, formData, { responseType: 'blob' });
  }

  extrairSavegnago(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/savegnago/extrair`, formData, { responseType: 'blob' });
  }

  extrairCema(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/cema/extrair`, formData, { responseType: 'blob' });
  }

  extrairMateus(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/mateus/extrair`, formData, { responseType: 'blob' });
  }

  extrairDrogaRaia(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/drogaraia/extrair`, formData, { responseType: 'blob' });
  }

  extrairAmazon(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/amazon/extrair`, formData, { responseType: 'blob' });
  }

  extrairGPA(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/gpa/extrair`, formData, { responseType: 'blob' });
  }

  conciliarProrrogacaoAtacadao(htmlFiles: File[], csvFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    for (const file of htmlFiles) {
        formData.append('html_files', file);
      }
    formData.append('csv_file', csvFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/atacadao/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoSendas(sendasFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('sendas_file', sendasFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/sendas/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoMartminas(martminasFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('martminas_file', martminasFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/martminas/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoSavegnago(savegnagoFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('savegnago_file', savegnagoFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/savegnago/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoCema(cemaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('cema_file', cemaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/cema/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoMateus(mateusFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('mateus_file', mateusFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/mateus/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarProrrogacaoDrogaRaia(drogaraiaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('drogaraia_file', drogaraiaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/drogaraia/conciliar`, formData, {
      responseType: 'blob'
    });
  }

  conciliarBancos(planilha: File, extratos: File[], idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('planilha', planilha);
    extratos.forEach((file) => {
      formData.append('extratos', file);
    });
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/conciliacao-pagamentos/conciliar-bancos`, formData, {
      responseType: 'blob'
    });
  }

  lerApb(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/conciliacao-pagamentos/ler-apb`, formData);
  }

  analisarUniversal(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/plano-saude/universal/analisar`, formData);
  }

  analisarSorriso(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/plano-saude/sorriso/analisar`, formData);
  }

  confirmarSorriso(nomeArquivo: string, titulares: any[], idEmpresa?: number, idUserInc?: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/plano-saude/sorriso/confirmar`, {
      nomeArquivo,
      titulares,
      idEmpresa,
      idUserInc
    });
  }

  exportarSorrisoExcel(titulares: any[]): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/plano-saude/sorriso/exportar`, { titulares }, {
      responseType: 'blob'
    });
  }

  analisarUnimedOdonto(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/plano-saude/unimed-odonto/analisar`, formData);
  }

  confirmarUnimedOdonto(nomeArquivo: string, titulares: any[], idEmpresa?: number, idUserInc?: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/plano-saude/unimed-odonto/confirmar`, {
      nomeArquivo,
      titulares,
      idEmpresa,
      idUserInc
    });
  }

  exportarUnimedOdontoExcel(titulares: any[]): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/plano-saude/unimed-odonto/exportar`, { titulares }, {
      responseType: 'blob'
    });
  }
}
