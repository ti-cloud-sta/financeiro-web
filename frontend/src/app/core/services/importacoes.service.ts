import { Injectable, NgZone } from '@angular/core';
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
  devolucao: string | null;
  idCliente: number | null;
  especie: string | null;
  carteira: string | null;
  idUnidade: number | null;
  serie: string | null;
  parccela: string | null;
  portador: string | null;
  dtEmissao: string | null;
  dtEntrega: string | null;
  valorOriginal: number | null;
  valorSaldo: number | null;
}

export interface HistoricoApi {
  idhistoricopendencia: number;
  idNfPendencias: number;
  tipo: string | null;
  observacao: string | null;
  createdAt: string | null;
  autor: string | null;
  thread_id?: string | null;
  message_id?: string | null;
}

export interface AnexoMensagem {
  nome: string;
  tamanho: number;
}

export interface MensagemThreadApi {
  id: string;
  thread_id: string;
  de: string;
  para: string;
  copia?: string;
  assunto: string;
  data: string;
  internal_date: number;
  corpo_html: string;
  corpo_texto: string;
  anexos: AnexoMensagem[];
  minha_mensagem: boolean;
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
  prorrogadas: number;
  atualizadas?: number;
  baixadas?: number;
  ignoradasSemCliente: number;
  ignoradasSemVencimento: number;
  ignoradasNaoVencidas?: number;
  ignoradasDuplicadas: number;
  semUnidadeEncontrada: number;
  clientesCriados: number;
  matrizesCriadas: number;
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

  constructor(private http: HttpClient, private zone: NgZone) {}

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

  obterDashboardVisaoGeral(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/inadimplencia/dashboard/visao-geral`);
  }

  alterarFasePendencia(id: number, fase: string, status?: string): Observable<{ idnfpendencias: number; fase: string }> {
    const payload: any = { fase };
    if (status) {
      payload.status = status;
    }
    return this.http.patch<{ idnfpendencias: number; fase: string }>(
      `${this.apiUrl}/inadimplencia/pendencias/${id}/fase`,
      payload
    );
  }

  listarHistoricoPendencia(idNf: number): Observable<HistoricoApi[]> {
    return this.http.get<HistoricoApi[]>(`${this.apiUrl}/inadimplencia/pendencias/${idNf}/historico`);
  }

  listarMensagensPendencia(idNf: number): Observable<MensagemThreadApi[]> {
    return this.http.get<MensagemThreadApi[]>(`${this.apiUrl}/inadimplencia/pendencias/${idNf}/mensagens`);
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

  enviarEmailPendencia(idNf: number, formData: FormData): Observable<{ sucesso: boolean; messageId?: string; threadId?: string }> {
    return this.http.post<{ sucesso: boolean; messageId?: string; threadId?: string }>(
      `${this.apiUrl}/inadimplencia/pendencias/${idNf}/enviar-email`,
      formData
    );
  }

  enviarEmailLote(idsNf: number[], formData: FormData): Observable<{ sucesso: boolean; total_titulos: number; messageId?: string; threadId?: string }> {
    formData.append('ids_nf', idsNf.join(','));
    return this.http.post<{ sucesso: boolean; total_titulos: number; messageId?: string; threadId?: string }>(
      `${this.apiUrl}/inadimplencia/pendencias/enviar-email-lote`,
      formData
    );
  }

  importarPendenciasInadimplencia(file: File): Observable<any> {
    return new Observable(observer => {
      const formData = new FormData();
      formData.append('file', file);
      
      const token = localStorage.getItem('erp_access_token') || localStorage.getItem('access_token');
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      fetch(`${this.apiUrl}/inadimplencia/importar-pendencias`, {
        method: 'POST',
        headers: headers,
        body: formData
      })
      .then(async response => {
        if (!response.ok) {
          throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder('utf-8');
        
        if (!reader) {
          throw new Error("Não foi possível ler a stream.");
        }
        
        // Um chunk pode terminar no meio de uma linha NDJSON: o pedaço final incompleto
        // fica no buffer e é completado pelo próximo chunk (ou processado ao fim da stream).
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            buffer += decoder.decode();
          } else {
            buffer += decoder.decode(value, { stream: true });
          }

          const lines = buffer.split('\n');
          buffer = done ? '' : (lines.pop() ?? '');

          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                if (data.erro) {
                   this.zone.run(() => observer.error(data.erro));
                   return;
                }
                this.zone.run(() => observer.next(data));
              } catch (e) {
                console.warn("Erro ao parsear chunk JSON", line);
              }
            }
          }

          if (done) break;
        }
        
        this.zone.run(() => observer.complete());
      })
      .catch(error => {
        this.zone.run(() => observer.error(error));
      });
    });
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
    return this.http.post(`${this.apiUrl}/cema/extrair`, formData, { responseType: 'blob' });
  }

  extrairMateus(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
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
    return this.http.post(`${this.apiUrl}/amazon/extrair`, formData, { responseType: 'blob' });
  }

  extrairGPA(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/gpa/extrair`, formData, { responseType: 'blob' });
  }

  extrairAdicao(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/adicao/extrair`, formData, { responseType: 'blob' });
  }

  extrairAtakarejo(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/atakarejo/extrair`, formData, { responseType: 'blob' });
  }

  extrairSonda(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    return this.extrairAtakarejo(empresaFile, acrFile, idUserInc);
  }

  extrairZeferino(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/zeferino/extrair`, formData, { responseType: 'blob' });
  }

  conciliarProrrogacaoAdicao(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/adicao/conciliar`, formData, { responseType: 'blob' });
  }

  conciliarProrrogacaoAtakarejo(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/atakarejo/conciliar`, formData, { responseType: 'blob' });
  }

  conciliarProrrogacaoSonda(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    return this.conciliarProrrogacaoAtakarejo(empresaFile, acrFile, idUserInc);
  }

  conciliarProrrogacaoZeferino(empresaFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('empresa_file', empresaFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/zeferino/conciliar`, formData, { responseType: 'blob' });
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

  conciliarProrrogacaoAmazon(amazonFile: File, acrFile: File, idUserInc?: number): Observable<Blob> {
    const formData = new FormData();
    formData.append('amazon_file', amazonFile);
    formData.append('acr_file', acrFile);
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }
    return this.http.post(`${this.apiUrl}/amazon/conciliar`, formData, {
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

  conciliarBancos(planilha: File, extratos: File[], idUserInc?: number): Observable<any> {
    const formData = new FormData();
    formData.append('planilha', planilha);
    extratos.forEach((file) => {
      formData.append('extratos', file);
    });
    if (idUserInc) {
      formData.append('idUserInc', idUserInc.toString());
    }

    return new Observable(observer => {
      const token = localStorage.getItem('erp_access_token');
      const headers: any = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      fetch(`${this.apiUrl}/conciliacao-pagamentos/conciliar-bancos`, {
        method: 'POST',
        headers: headers,
        body: formData
      })
      .then(async response => {
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          observer.error({ error: errorData, status: response.status });
          return;
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        if (!reader) {
          observer.error(new Error('Nativo de stream não suportado pelo navegador.'));
          return;
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Maintain incomplete chunk

          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                if (data.error) {
                   observer.error(data);
                   return;
                }
                observer.next(data);
              } catch (e) {
                console.error('Erro ao parsear chunk NDJSON:', e, line);
              }
            }
          }
        }
        observer.complete();
      })
      .catch(err => {
        observer.error(err);
      });
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

  confirmarSorriso(nomeArquivo: string, titulares: any[], idEmpresa?: number, idUnidade?: number, idUserInc?: number, dataCompetencia?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/plano-saude/sorriso/confirmar`, {
      nomeArquivo,
      titulares,
      idEmpresa,
      idUnidade,
      idUserInc,
      dataCompetencia
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

  confirmarUnimedOdonto(nomeArquivo: string, titulares: any[], idEmpresa?: number, idUnidade?: number, idUserInc?: number, dataCompetencia?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/plano-saude/unimed-odonto/confirmar`, {
      nomeArquivo,
      titulares,
      idEmpresa,
      idUnidade,
      idUserInc,
      dataCompetencia
    });
  }

  exportarUnimedOdontoExcel(titulares: any[]): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/plano-saude/unimed-odonto/exportar`, { titulares }, {
      responseType: 'blob'
    });
  }
}
