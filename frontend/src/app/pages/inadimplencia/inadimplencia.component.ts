import { Component, OnInit, signal, computed, ViewChild, ElementRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PendenciasComponent } from './components/pages/pendencias/pendencias.component';
import { NgxEchartsModule } from 'ngx-echarts';
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { AvatarComponent } from '../../shared/components/avatar/avatar.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { ImportacoesService, Importacao, ImportacaoPendenciasResponse, MensagemThreadApi } from '../../core/services/importacoes.service';

export interface MensagemChat {
  id: number;
  autor: string;
  iniciais: string;
  minhaMensagem: boolean;
  data: Date;
  assunto: string;
  corpo: string;
  anexos: string[];
}

@Component({
  selector: 'app-inadimplencia',
  standalone: true,
  imports: [CommonModule, FormsModule, PendenciasComponent, ButtonComponent, ConfirmModalComponent, ModalComponent, NgxEchartsModule, SkeletonComponent, AvatarComponent],
  templateUrl: './inadimplencia.component.html',
  styleUrls: ['./inadimplencia.component.scss']
})
export class InadimplenciaComponent implements OnInit {
  private importacoesService = inject(ImportacoesService);

  isSidebarCollapsed = false;
  activeTab = 'dashboards';
  dashboardTab = signal<'visao-geral' | 'financeiro' | 'logistica' | 'comercial' | 'pendencias-acr'>('visao-geral');
  financeiroTab = signal<'gerencial' | 'gerente'>('gerencial');
  pendenciasAcrTab = signal<'atrasados' | 'protestados' | 'sem_data_entrega' | 'devolucao' | 'acordo' | 'an' | 'ad' | 'rj' | 'pr'>('atrasados');

  // Modal Tratativas
  isTratativasModalOpen = false;
  tituloSelecionadoTratativas: any = null;
  tratativasMock: any[] = [];

  // Modal Mensagens
  isMensagensModalOpen = false;
  tituloSelecionadoMensagens: any = null;
  mensagensMock: MensagemChat[] = [];
  isLoadingMensagens = false;

  // Modal Histórico
  isHistoricoModalOpen = false;
  tituloSelecionadoHistorico: any = null;
  historicoMock: any[] = [];
  isLoadingHistorico = false;

  ngOnInit() {
    this.isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    this.carregarHistoricoAtualizacao();
    this.carregarDashboardVisaoGeral();
  }

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  setActiveTab(tab: string) {
    this.activeTab = tab;
    if (tab === 'dashboards') {
      this.setDashboardTab(this.dashboardTab());
    }
  }

  setDashboardTab(tab: 'visao-geral' | 'financeiro' | 'logistica' | 'comercial' | 'pendencias-acr') {
    this.dashboardTab.set(tab);
    
    this.isDashboardLoading.set(true);
    setTimeout(() => {
      this.isDashboardLoading.set(false);
      
      if (tab === 'visao-geral') {
        this._loadFinanceiroData();
        this._loadLogisticaData();
        this._loadComercialData();
      } else if (tab === 'financeiro') {
        this._loadFinanceiroData();
      } else if (tab === 'logistica') {
        this._loadLogisticaData();
      } else if (tab === 'comercial') {
        this._loadComercialData();
      }
    }, 600);
  }

  // ----------------------------------------------------
  // AtualizaÃƒÂ§ÃƒÂ£o de Dados
  // ----------------------------------------------------
  @ViewChild('atualizacaoFileInput') atualizacaoFileInput!: ElementRef<HTMLInputElement>;
  @ViewChild(PendenciasComponent) pendenciasComponent?: PendenciasComponent;

  selectedFileAtualizacao = signal<File | null>(null);
  searchAtualizacao = signal<string>('');
  atualizacaoHistory = signal<Importacao[]>([]);
  isImportandoDados = signal<boolean>(false);
  importacaoProgressMsg = signal<string>('');
  importacaoProgressPercent = signal<number>(0);

  filteredAtualizacaoHistory = computed(() => {
    const term = this.searchAtualizacao().toLowerCase().trim();
    if (!term) return this.atualizacaoHistory();
    return this.atualizacaoHistory().filter(h =>
      h.nomeArquivo.toLowerCase().includes(term) ||
      h.tipo.toLowerCase().includes(term)
    );
  });

  carregarHistoricoAtualizacao() {
    this.importacoesService.listar(1, 50, undefined, 'PENDENCIAS').subscribe({
      next: (res) => this.atualizacaoHistory.set(res.items || []),
      error: (err) => console.error('Erro ao carregar historico de atualizaÃƒÂ§ÃƒÂµes de dados:', err)
    });
  }

  formatarData(dataIso: string): string {
    const d = new Date(dataIso);
    if (isNaN(d.getTime())) return dataIso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  triggerUploadAtualizacao() {
    if (this.isImportandoDados()) return;
    if (this.atualizacaoFileInput) {
      this.atualizacaoFileInput.nativeElement.value = '';
      this.atualizacaoFileInput.nativeElement.click();
    }
  }

  onFileSelectedAtualizacao(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFileAtualizacao.set(input.files[0]);
    }
  }

  processarAtualizacaoDados() {
    const arquivo = this.selectedFileAtualizacao();
    if (!arquivo || this.isImportandoDados()) return;

    this.isImportandoDados.set(true);
    this.importacaoProgressMsg.set('Iniciando envio e processamento...');
    this.importacaoProgressPercent.set(0);
    
    let lastRes: any = null;

    this.importacoesService.importarPendenciasInadimplencia(arquivo).subscribe({
      next: (res) => {
        if (res && res.sucesso) {
          lastRes = res;
        } else if (res && res.progresso !== undefined) {
          const progMsg = `Processando linha ${res.progresso} de ${res.total}... Prorrogadas: ${res.prorrogadas || 0}` + (res.atualizadas ? ` | Atualizadas: ${res.atualizadas}` : '');
          this.importacaoProgressMsg.set(progMsg);
          if (res.total > 0) {
            this.importacaoProgressPercent.set(Math.round((res.progresso / res.total) * 100));
          }
        }
      },
      error: (err) => {
        this.isImportandoDados.set(false);
        this.importacaoProgressMsg.set('');
        this.importacaoProgressPercent.set(0);
        console.error('Erro ao importar pendências:', err);
        this.openAlert('Erro na Importação', this.extractErrorMessage(err), 'danger');
      },
      complete: () => {
        this.isImportandoDados.set(false);
        this.importacaoProgressMsg.set('');
        this.importacaoProgressPercent.set(0);
        this.selectedFileAtualizacao.set(null);
        this.carregarHistoricoAtualizacao();
        
        // Redireciona e atualiza a tela de pendências imediatamente
        this.activeTab = 'pendencias';
        setTimeout(() => {
          this.pendenciasComponent?.carregarPendencias();
        }, 100);
        
        if (lastRes) {
          this.openAlert('Importação Concluída', this.montarResumoImportacao(lastRes), 'primary');
        }
      }
    });
  }

  private montarResumoImportacao(res: ImportacaoPendenciasResponse): string {
    const linhas = [
      `• Linhas com título: ${res.totalLinhasComEspecie}`,
      `• Importadas (Novas): ${res.importadas}`,
      `• Prorrogadas (Vencimento): ${res.prorrogadas || 0}`,
      `• Atualizadas (Saldo / Carteira): ${res.atualizadas || 0}`,
      `• Títulos Baixados (Encerrados): ${res.baixadas || 0}`,
      `• Ignoradas (A vencer / Não vencidas): ${res.ignoradasNaoVencidas || 0}`,
      `• Ignoradas (Sem alterações): ${res.ignoradasDuplicadas}`,
      `• Ignoradas (Sem vencimento): ${res.ignoradasSemVencimento}`,
      `• Clientes criados: ${res.clientesCriados}`,
      `• Matrizes criadas: ${res.matrizesCriadas}`
    ];
    return linhas.join('\n');
  }

  private extractErrorMessage(err: any): string {
    if (typeof err === 'string') return err;
    if (err && err.error) {
      if (typeof err.error.detail === 'string') {
        return err.error.detail;
      }
      if (Array.isArray(err.error.detail)) {
        return err.error.detail.map((d: any) => `${d.loc?.join('.') || ''}: ${d.msg}`).join('\n');
      }
      if (err.error.message) {
        return err.error.message;
      }
    }
    return err?.message || 'Erro desconhecido no servidor';
  }

  excluirAtualizacao(id: number) {
    this.openConfirmModal(
      'Confirmar Exclusão',
      'Tem certeza que deseja excluir esta atualização? Esta ação é irreversível.',
      () => {
        this.closeConfirmModal();
        this.importacoesService.excluir(id).subscribe({
          next: () => {
            this.carregarHistoricoAtualizacao();
          },
          error: (err) => {
            console.error('Erro ao excluir atualização de dados', err);
            this.openAlert('Erro', 'Não foi possível excluir o registro.', 'danger');
          }
        });
      },
      'danger'
    );
  }

  // ----------------------------------------------------
  // Confirm/Alert Modal (genÃƒÂ©rico)
  // ----------------------------------------------------
  isConfirmModalOpen = false;
  confirmTitle = '';
  confirmMessage = '';
  confirmText = 'Confirmar';
  cancelText = 'Cancelar';
  confirmVariant: 'danger' | 'primary' = 'primary';
  showCancelConfirm = true;
  confirmCallback: () => void = () => {};

  openConfirmModal(title: string, message: string, onConfirm: () => void, variant: 'danger' | 'primary' = 'danger') {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmText = 'Confirmar';
    this.cancelText = 'Cancelar';
    this.confirmVariant = variant;
    this.showCancelConfirm = true;
    this.confirmCallback = onConfirm;
    this.isConfirmModalOpen = true;
  }

  openAlert(title: string, message: string, variant: 'danger' | 'primary' = 'primary') {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmText = 'Ok';
    this.cancelText = '';
    this.confirmVariant = variant;
    this.showCancelConfirm = false;
    this.confirmCallback = () => this.closeConfirmModal();
    this.isConfirmModalOpen = true;
  }

  closeConfirmModal() {
    this.isConfirmModalOpen = false;
  }

  executeConfirm() {
    this.confirmCallback();
  }

  // ----------------------------------------------------
  // Dashboards - MOCK DATA
  // ----------------------------------------------------
  isDashboardLoading = signal<boolean>(false);
  colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899', '#06b6d4', '#8b5cf6', '#f43f5e'];

  // Visao Geral / Financeiro (Gerencial)
  dataHoje: Date = new Date();
  kpiTotalVencidoAtual = 0;
  kpiTotalProtestadoAtual = 0;
  qtdTitulosVencidos = 0;
  qtdTitulosProtestados = 0;
  evolucaoVencido = 0;
  evolucaoProtestado = 0;

  // KPIs Logística Atual
  kpiSemEntregaAtual = 0;
  evolucaoSemEntrega = 0;
  kpiDevolucaoAtual = 0;
  evolucaoDevolucao = 0;

  chartOptionsAtrasoAnual: any;
  chartOptionsFaixasAtraso: any;
  chartOptionsProtestos: any;
  rankingClientes: any[] = [];
  rankingGerentes: any[] = [];
  rankingRepresentantes: any[] = [];
  rankingGerentesAtraso: any[] = [];
  rankingGerentesProtesto: any[] = [];
  rankingRepresentantesAtraso: any[] = [];
  rankingRepresentantesProtesto: any[] = [];
  chartOptionsGerenteAtraso: any;
  chartOptionsGerenteFaixas: any;
  maioresAtrasos: any[] = [];
  
  // Paginação Visão Geral (Financeiro) - Atrasados
  searchFinanceiroAtrasado = '';
  pageFinanceiroAtrasado = 1;

  get paginatedFinanceiroAtrasado() {
    const s = this.searchFinanceiroAtrasado.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'ATRASADO');
    if (s) {
      filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    }
    const start = (this.pageFinanceiroAtrasado - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesFinanceiroAtrasado() {
    const s = this.searchFinanceiroAtrasado.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'ATRASADO');
    if (s) {
      filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    }
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // Paginação Visão Geral (Financeiro) - Protestados
  searchFinanceiroProtestado = '';
  pageFinanceiroProtestado = 1;

  get paginatedFinanceiroProtestado() {
    const s = this.searchFinanceiroProtestado.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'PROTESTADO');
    if (s) {
      filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    }
    const start = (this.pageFinanceiroProtestado - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesFinanceiroProtestado() {
    const s = this.searchFinanceiroProtestado.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'PROTESTADO');
    if (s) {
      filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    }
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // Visão por Carteira (Gerente/Representante)
  gridCarteira: any[] = [];
  searchCarteira = '';
  pageCarteira = 1;
  kpiTotalVencidoCarteira = 0;
  kpiTotalProtestadoCarteira = 0;

  // Concentração de Inadimplência e Títulos Vencidos da Carteira
  gerenteMaiorAtraso: { nome: string; qtd: number; valor: number } | null = null;
  representanteMaiorAtraso: { nome: string; qtd: number; valor: number } | null = null;
  gerentesMaisVencidos: Array<{ nome: string; qtd: number; valor: number }> = [];
  representantesMaisVencidos: Array<{ nome: string; qtd: number; valor: number }> = [];

  get paginatedCarteira() {
    const s = this.searchCarteira.toLowerCase();
    const filtered = s ? this.gridCarteira.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s)) : this.gridCarteira;
    const start = (this.pageCarteira - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesCarteira() {
    const s = this.searchCarteira.toLowerCase();
    const filtered = s ? this.gridCarteira.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s)) : this.gridCarteira;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // Logistica
  kpiSemEntrega = 0;
  kpiDevolucao = 0;
  chartOptionsSemEntrega: any;
  chartOptionsDevolucao: any;
  gridSemEntrega: any[] = [];
  gridDevolucao: any[] = [];
  
  // Paginação Logística
  searchSemEntrega = '';
  searchDevolucao = '';
  pageSemEntrega = 1;
  pageDevolucao = 1;
  pageSize = 10;

  get paginatedSemEntrega() {
    const s = this.searchSemEntrega.toLowerCase();
    const filtered = s ? this.gridSemEntrega.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridSemEntrega;
    const start = (this.pageSemEntrega - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesSemEntrega() {
    const s = this.searchSemEntrega.toLowerCase();
    const filtered = s ? this.gridSemEntrega.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridSemEntrega;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  get paginatedDevolucao() {
    const s = this.searchDevolucao.toLowerCase();
    const filtered = s ? this.gridDevolucao.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridDevolucao;
    const start = (this.pageDevolucao - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesDevolucao() {
    const s = this.searchDevolucao.toLowerCase();
    const filtered = s ? this.gridDevolucao.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridDevolucao;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // Comercial
  kpiTotalAcordos = 0;
  rankingAcordos: any[] = [];
  kpiConcentracaoClientes: any[] = [];
  chartOptionsAcordos: any;
  gridAcordos: any[] = [];
  searchAcordos = '';
  pageAcordos = 1;

  get paginatedAcordos() {
    const s = this.searchAcordos.toLowerCase();
    const filtered = s ? this.gridAcordos.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAcordos;
    const start = (this.pageAcordos - 1) * this.pageSize;
    return filtered.slice(start, start + this.pageSize);
  }

  get totalPagesAcordos() {
    const s = this.searchAcordos.toLowerCase();
    const filtered = s ? this.gridAcordos.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAcordos;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // ==========================================
  // ESTADOS E PAGINAÇÃO PARA PENDÊNCIAS ACR
  // ==========================================
  searchAcrAtrasados = ''; pageAcrAtrasados = 1;
  get paginatedAcrAtrasados() {
    const s = this.searchAcrAtrasados.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'ATRASADO');
    if (s) filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    return filtered.slice((this.pageAcrAtrasados - 1) * this.pageSize, this.pageAcrAtrasados * this.pageSize);
  }
  get totalPagesAcrAtrasados() {
    const s = this.searchAcrAtrasados.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'ATRASADO');
    if (s) filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  searchAcrProtestados = ''; pageAcrProtestados = 1;
  get paginatedAcrProtestados() {
    const s = this.searchAcrProtestados.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'PROTESTADO' || t.status === 'CARTÓRIO');
    if (s) filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    return filtered.slice((this.pageAcrProtestados - 1) * this.pageSize, this.pageAcrProtestados * this.pageSize);
  }
  get totalPagesAcrProtestados() {
    const s = this.searchAcrProtestados.toLowerCase();
    let filtered = this.maioresAtrasos.filter(t => t.status === 'PROTESTADO' || t.status === 'CARTÓRIO');
    if (s) filtered = filtered.filter(t => t.titulo.toLowerCase().includes(s) || t.cliente.toLowerCase().includes(s));
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  searchAcrSemEntrega = ''; pageAcrSemEntrega = 1;
  get paginatedAcrSemEntrega() {
    const s = this.searchAcrSemEntrega.toLowerCase();
    const filtered = s ? this.gridSemEntrega.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridSemEntrega;
    return filtered.slice((this.pageAcrSemEntrega - 1) * this.pageSize, this.pageAcrSemEntrega * this.pageSize);
  }
  get totalPagesAcrSemEntrega() {
    const s = this.searchAcrSemEntrega.toLowerCase();
    const filtered = s ? this.gridSemEntrega.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridSemEntrega;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  searchAcrDevolucao = ''; pageAcrDevolucao = 1;
  get paginatedAcrDevolucao() {
    const s = this.searchAcrDevolucao.toLowerCase();
    const filtered = s ? this.gridDevolucao.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridDevolucao;
    return filtered.slice((this.pageAcrDevolucao - 1) * this.pageSize, this.pageAcrDevolucao * this.pageSize);
  }
  get totalPagesAcrDevolucao() {
    const s = this.searchAcrDevolucao.toLowerCase();
    const filtered = s ? this.gridDevolucao.filter(g => g.titulo.toLowerCase().includes(s) || g.cliente.toLowerCase().includes(s)) : this.gridDevolucao;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  searchAcrAcordo = ''; pageAcrAcordo = 1;
  get paginatedAcrAcordo() {
    const s = this.searchAcrAcordo.toLowerCase();
    const filtered = s ? this.gridAcordos.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAcordos;
    return filtered.slice((this.pageAcrAcordo - 1) * this.pageSize, this.pageAcrAcordo * this.pageSize);
  }
  get totalPagesAcrAcordo() {
    const s = this.searchAcrAcordo.toLowerCase();
    const filtered = s ? this.gridAcordos.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAcordos;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  // Os próximos (AN, AD, RJ, PR) não têm fonte de dados clara ainda, então ficam vazios
  gridAN: any[] = []; searchAcrAN = ''; pageAcrAN = 1;
  get paginatedAcrAN() {
    const s = this.searchAcrAN.toLowerCase();
    const filtered = s ? this.gridAN.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAN;
    return filtered.slice((this.pageAcrAN - 1) * this.pageSize, this.pageAcrAN * this.pageSize);
  }
  get totalPagesAcrAN() {
    const s = this.searchAcrAN.toLowerCase();
    const filtered = s ? this.gridAN.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAN;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  gridAD: any[] = []; searchAcrAD = ''; pageAcrAD = 1;
  get paginatedAcrAD() {
    const s = this.searchAcrAD.toLowerCase();
    const filtered = s ? this.gridAD.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAD;
    return filtered.slice((this.pageAcrAD - 1) * this.pageSize, this.pageAcrAD * this.pageSize);
  }
  get totalPagesAcrAD() {
    const s = this.searchAcrAD.toLowerCase();
    const filtered = s ? this.gridAD.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridAD;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  gridRJ: any[] = []; searchAcrRJ = ''; pageAcrRJ = 1;
  get paginatedAcrRJ() {
    const s = this.searchAcrRJ.toLowerCase();
    const filtered = s ? this.gridRJ.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridRJ;
    return filtered.slice((this.pageAcrRJ - 1) * this.pageSize, this.pageAcrRJ * this.pageSize);
  }
  get totalPagesAcrRJ() {
    const s = this.searchAcrRJ.toLowerCase();
    const filtered = s ? this.gridRJ.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridRJ;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }

  gridPR: any[] = []; searchAcrPR = ''; pageAcrPR = 1;
  get paginatedAcrPR() {
    const s = this.searchAcrPR.toLowerCase();
    const filtered = s ? this.gridPR.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridPR;
    return filtered.slice((this.pageAcrPR - 1) * this.pageSize, this.pageAcrPR * this.pageSize);
  }
  get totalPagesAcrPR() {
    const s = this.searchAcrPR.toLowerCase();
    const filtered = s ? this.gridPR.filter(a => (a.titulo?.toLowerCase().includes(s)) || (a.cliente?.toLowerCase().includes(s))) : this.gridPR;
    return Math.ceil(filtered.length / this.pageSize) || 1;
  }


  carregarDashboardVisaoGeral() {
    this.isDashboardLoading.set(true);
    setTimeout(() => {
      this.isDashboardLoading.set(false);
      this._loadFinanceiroData();
      this._loadLogisticaData();
      this._loadComercialData();
    }, 600);
  }


  isLoadingTratativas = false;

  abrirTratativas(titulo: any) {
    this.tituloSelecionadoTratativas = titulo;
    this.tratativasMock = []; // We can rename this to tratativasReais, but to not break HTML let's keep it or rename it. Let's just use tratativasMock as the array.
    this.isTratativasModalOpen = true;
    this.isLoadingTratativas = true;

    if (titulo.id) {
      this.importacoesService.listarTratativas(Number(titulo.id)).subscribe({
        next: (itens) => {
          this.tratativasMock = itens.map((t: any) => ({
            id: t.idtratativas,
            data: t.createdAt ? new Date(t.createdAt) : new Date(),
            autor: t.autor || 'Usuário',
            conteudo: t.conteudo
          }));
          this.isLoadingTratativas = false;
        },
        error: (err) => {
          console.error('Erro ao carregar tratativas:', err);
          this.isLoadingTratativas = false;
        }
      });
    } else {
      this.isLoadingTratativas = false;
    }
  }

  fecharTratativas() {
    this.isTratativasModalOpen = false;
    this.tituloSelecionadoTratativas = null;
  }

  getBadgeClass(fase: string | null | undefined): string {
    if (!fase) return 'bg-light text-secondary border border-secondary-subtle';
    const f = fase.toUpperCase();
    if (f === 'ACORDO') return 'bg-success bg-opacity-10 text-success border border-success-subtle';
    if (f === 'PROTESTADO' || f === 'DEVOLUCAO' || f === 'ATRASADO') return 'bg-danger bg-opacity-10 text-danger border border-danger-subtle';
    if (f === 'SEM DATA DE ENTREGA') return 'bg-warning bg-opacity-10 text-warning border border-warning-subtle';
    return 'bg-primary bg-opacity-10 text-primary border border-primary-subtle';
  }

  abrirMensagens(titulo: any) {
    this.tituloSelecionadoMensagens = titulo;
    this.mensagensMock = [];
    this.isMensagensModalOpen = true;
    this.isLoadingMensagens = true;

    if (titulo.id) {
      this.importacoesService.listarMensagensPendencia(Number(titulo.id)).subscribe({
        next: (itens) => {
          this.mensagensMock = itens.map(m => this.mapearMensagemApi(m));
          this.isLoadingMensagens = false;
        },
        error: (err) => {
          console.error('Erro ao carregar mensagens:', err);
          this.isLoadingMensagens = false;
        }
      });
    } else {
      this.isLoadingMensagens = false;
    }
  }

  fecharMensagens() {
    this.isMensagensModalOpen = false;
    this.tituloSelecionadoMensagens = null;
    this.mensagensMock = [];
  }

  private mapearMensagemApi(m: MensagemThreadApi): MensagemChat {
    const autor = this.extrairNomeEmail(m.de);
    return {
      id: m.internal_date,
      autor,
      iniciais: this.obterIniciais(autor),
      minhaMensagem: m.minha_mensagem,
      data: new Date(m.internal_date * 1000),
      assunto: m.assunto,
      corpo: m.corpo_html || m.corpo_texto.replace(/\n/g, '<br>'),
      anexos: m.anexos ? m.anexos.map((a: any) => a.nome) : []
    };
  }

  private extrairNomeEmail(de: string): string {
    if (!de) return 'Desconhecido';
    const match = de.match(/^(.*?)\s*</);
    if (match && match[1]) {
      return match[1].replace(/["']/g, '').trim();
    }
    return de.trim();
  }

  private obterIniciais(nome: string): string {
    if (!nome) return '?';
    const partes = nome.split(' ').filter(p => p.length > 0);
    if (partes.length === 1) return partes[0].substring(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
  }

  abrirHistorico(titulo: any) {
    this.tituloSelecionadoHistorico = titulo;
    this.historicoMock = [];
    this.isLoadingHistorico = true;
    this.isHistoricoModalOpen = true;

    if (titulo?.id) {
      this.importacoesService.listarHistoricoPendencia(Number(titulo.id)).subscribe({
        next: (itens) => {
          this.isLoadingHistorico = false;
          this.historicoMock = (itens || []).map((h: any) => {
            const { icone, cor } = this.iconeCorPorTipo(h.tipo);
            return {
              data: h.createdAt ? new Date(h.createdAt) : new Date(),
              tipo: h.tipo || 'Evento',
              observacao: h.observacao || '',
              icone,
              cor
            };
          });
        },
        error: (err) => {
          this.isLoadingHistorico = false;
          console.error('Erro ao carregar histórico:', err);
          this.historicoMock = [];
        }
      });
    } else {
      this.isLoadingHistorico = false;
    }
  }

  private iconeCorPorTipo(tipo: string | null): { icone: string; cor: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'secondary' } {
    const t = (tipo || '').toLowerCase();
    if (t.includes('finaliza') || t.includes('resolu')) {
      return { icone: 'fa-solid fa-check-circle', cor: 'success' };
    }
    if (t.includes('email') || t.includes('e-mail') || t.includes('mensagem')) {
      return { icone: 'fa-solid fa-envelope', cor: 'primary' };
    }
    if (t.includes('prorrogad')) return { icone: 'fa-regular fa-calendar-plus', cor: 'warning' };
    if (t.includes('importada')) return { icone: 'fa-solid fa-file-circle-plus', cor: 'primary' };
    if (t.includes('fase') || t.includes('classifica')) return { icone: 'fa-solid fa-shuffle', cor: 'info' };
    if (t.includes('status')) return { icone: 'fa-solid fa-flag', cor: 'warning' };
    if (t.includes('tratativa')) return { icone: 'fa-solid fa-headset', cor: 'success' };
    return { icone: 'fa-solid fa-circle-info', cor: 'secondary' };
  }

  fecharHistorico() {
    this.isHistoricoModalOpen = false;
    this.tituloSelecionadoHistorico = null;
    this.isLoadingHistorico = false;
  }

  private _loadFinanceiroData() {
    this.importacoesService.obterDashboardVisaoGeral().subscribe({
      next: (res) => {
        this.dataHoje = new Date();
        this.kpiTotalVencidoAtual = res.kpiVencido;
        this.evolucaoVencido = res.kpiVencidoEvolucao;
        this.kpiTotalProtestadoAtual = res.kpiProtestado;
        this.evolucaoProtestado = res.kpiProtestadoEvolucao;
        this.qtdTitulosVencidos = (res.gridFinanceiro || []).length;
        this.qtdTitulosProtestados = (res.gridFinanceiro || []).filter((x: any) => x.status === 'PROTESTADO' || x.status === 'CARTÓRIO').length;

        this.rankingClientes = (res.rankingClientesAtraso || []).map((x: any) => ({
          nome: x.cliente,
          qtd: x.qtd !== undefined && x.qtd !== null ? x.qtd : 1,
          valor: x.valor
        }));
        
        this.rankingGerentesAtraso = res.rankingGerentesAtraso;
        this.rankingGerentesProtesto = res.rankingGerentesProtesto;
        this.rankingRepresentantesAtraso = res.rankingRepresentantesAtraso;
        this.rankingRepresentantesProtesto = res.rankingRepresentantesProtesto;

        // Contagem de títulos por cliente na lista como fallback caso backend não envie
        const qtdPorCliente: Record<string, number> = {};
        for (const item of (res.gridFinanceiro || [])) {
          const cli = item.cliente || 'Desconhecido';
          qtdPorCliente[cli] = (qtdPorCliente[cli] || 0) + 1;
        }

        this.maioresAtrasos = (res.gridFinanceiro || []).map((x: any) => {
          const statusColorMap: Record<string, string> = {
            'ATRASADO': 'warning',
            'PROTESTADO': 'danger',
            'PRORROGADO': 'info',
            'OK': 'success',
            'ACORDO': 'primary',
            'DEVOLUCAO': 'warning',
            'SEM DATA DE ENTREGA': 'warning',
          };
          const statusColor = statusColorMap[x.status] || 'secondary';
          const venc = x.vencimento ? new Date(x.vencimento + 'T00:00:00') : null;
          const diasAtraso = venc ? Math.floor((new Date().getTime() - venc.getTime()) / 86400000) : null;
          const qtd = x.qtd !== undefined && x.qtd !== null ? x.qtd : (qtdPorCliente[x.cliente] || 1);
          return {
            ...x,
            qtd,
            statusColor,
            diasAtraso,
            isCartorio: x.status === 'CARTÓRIO' || x.status === 'PROTESTADO'
          };
        });

        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const textColor = isDark ? '#e2e8f0' : '#475569';
        const splitLineColor = isDark ? '#334155' : '#e2e8f0';

        this.chartOptionsAtrasoAnual = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: res.evolucaoAtraso.labels, axisLabel: { color: textColor } },
          yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: textColor } },
          series: [{ name: 'Vencidos', type: 'line', data: res.evolucaoAtraso.values, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: '#64748b' }, itemStyle: { color: this.colors[2] }, areaStyle: { opacity: 0.1 } }]
        };

        this.chartOptionsProtestos = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: res.evolucaoProtesto.labels, axisLabel: { color: textColor } },
          yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: textColor } },
          series: [{ name: 'Protestados', type: 'line', data: res.evolucaoProtesto.values, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: '#64748b' }, itemStyle: { color: this.colors[7] }, areaStyle: { opacity: 0.1 } }]
        };

        const totalFaixas = res.faixasAtraso.ate5 + res.faixasAtraso.ate15 + res.faixasAtraso.ate30 + res.faixasAtraso.acima30;

        let faixasData = [];
        if (totalFaixas === 0) {
          faixasData = [{ name: 'Sem títulos vencidos', value: 1, itemStyle: { color: splitLineColor }, label: { show: false }, tooltip: { show: false } }];
        } else {
          faixasData = [
            { name: 'Até 5 dias', value: res.faixasAtraso.ate5, itemStyle: { color: this.colors[1] } },
            { name: 'Até 15 dias', value: res.faixasAtraso.ate15, itemStyle: { color: this.colors[2] } },
            { name: '16 a 30 dias', value: res.faixasAtraso.ate30, itemStyle: { color: this.colors[4] } },
            { name: 'Acima de 30 dias', value: res.faixasAtraso.acima30, itemStyle: { color: this.colors[3] } }
          ];
        }

        this.chartOptionsFaixasAtraso = {
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          legend: { bottom: 0, textStyle: { color: textColor }, itemGap: 15 },
          series: [{
            type: 'pie',
            center: ['50%', '40%'],
            radius: ['45%', '65%'],
            avoidLabelOverlap: true,
            minAngle: 5,
            itemStyle: { borderRadius: 5, borderColor: 'transparent', borderWidth: 2 },
            label: { 
              color: textColor,
              formatter: '{b}\n{d}%',
              lineHeight: 16,
              alignTo: 'labelLine'
            },
            labelLine: {
              lineStyle: { color: textColor },
              smooth: 0.2,
              length: 15,
              length2: 15
            },
            data: faixasData
          }]
        };

        this.chartOptionsGerenteAtraso = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: ['Até 15 dias', '16 a 30 dias', '31 a 60 dias', 'Acima de 60 dias'] },
          yAxis: { type: 'value', splitLine: { show: false } },
          series: [{ name: 'Atraso (R$)', type: 'bar', data: [85000, 120000, 95000, 45000], itemStyle: { color: this.colors[3], borderRadius: [4, 4, 0, 0] }, label: { show: true, position: 'top', formatter: 'R$ {@score}' } }]
        };

        this.chartOptionsGerenteFaixas = {
          tooltip: { trigger: 'item' },
          legend: { top: 'bottom' },
          series: [{
            type: 'pie', radius: ['40%', '70%'],
            itemStyle: { borderRadius: 5, borderColor: 'transparent', borderWidth: 2 },
            label: { color: 'inherit', textBorderColor: 'transparent', textBorderWidth: 0 },
            data: [
              { name: 'Cobrança', value: 145, itemStyle: { color: this.colors[1] } },
              { name: 'Cartório', value: 89, itemStyle: { color: this.colors[2] } },
              { name: 'Protestado', value: 56, itemStyle: { color: this.colors[7] } }
            ]
          }]
        };
      },
      error: (err) => console.error('Erro ao carregar dados do dashboard financeiro:', err)
    });
  }

  carregarDashboardLogistica() {
    this.isDashboardLoading.set(true);
    setTimeout(() => {
      this.isDashboardLoading.set(false);
      this._loadLogisticaData();
    }, 600);
  }

  private _loadLogisticaData() {
      // Limpando os mocks, os dados reais vêm do subscribe abaixo.

    this.importacoesService.obterDashboardVisaoGeral().subscribe({
      next: (res) => {
        this.kpiSemEntregaAtual = res.evolucaoLogisticaSemEntrega.values[res.evolucaoLogisticaSemEntrega.values.length - 1]; 
        this.evolucaoSemEntrega = 0; // Evolução será calculada via histórico
        this.kpiDevolucaoAtual = res.evolucaoLogisticaDevolucao.values[res.evolucaoLogisticaDevolucao.values.length - 1]; 
        this.evolucaoDevolucao = 0;

        this.kpiSemEntrega = res.kpiSemEntrega;
        this.kpiDevolucao = res.kpiDevolucao;

        this.gridSemEntrega = res.gridSemEntrega;
        this.gridDevolucao = res.gridDevolucao;

        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const textColor = isDark ? '#e2e8f0' : '#475569';

        this.chartOptionsSemEntrega = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', boundaryGap: false, data: res.evolucaoLogisticaSemEntrega.labels, axisLabel: { color: textColor } },
          yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: textColor } },
          series: [{ name: 'Sem Entrega', type: 'line', data: res.evolucaoLogisticaSemEntrega.values, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: '#64748b' }, itemStyle: { color: this.colors[2] }, areaStyle: { opacity: 0.1 } }]
        };

        this.chartOptionsDevolucao = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', boundaryGap: false, data: res.evolucaoLogisticaDevolucao.labels, axisLabel: { color: textColor } },
          yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: textColor } },
          series: [{ name: 'Devolução', type: 'line', data: res.evolucaoLogisticaDevolucao.values, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: '#64748b' }, itemStyle: { color: this.colors[7] }, areaStyle: { opacity: 0.1 } }]
        };
      },
      error: (err) => console.error('Erro ao carregar dados do dashboard logístico:', err)
    });
  }

  carregarDashboardComercial() {
    this.isDashboardLoading.set(true);
    setTimeout(() => {
      this.isDashboardLoading.set(false);
      this._loadComercialData();
    }, 600);
  }

  private _loadComercialData() {
    this.importacoesService.obterDashboardVisaoGeral().subscribe({
      next: (res) => {
        this.kpiTotalAcordos = res.kpiTotalAcordos;
        
        this.rankingAcordos = res.rankingAcordos;

        // Grid Acordos vindo diretamente do backend
        this.gridAcordos = (res.gridAcordos || []).map((x: any) => ({
          ...x,
          statusColor: 'primary'
        }));

        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const textColor = isDark ? '#e2e8f0' : '#475569';

        this.chartOptionsAcordos = {
          tooltip: { trigger: 'axis' },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: { type: 'category', data: res.evolucaoAcordos.labels, axisLabel: { color: textColor } },
          yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: textColor } },
          series: [{ name: 'Acordos (Ocorrências)', type: 'line', data: res.evolucaoAcordos.values, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: '#64748b' }, itemStyle: { color: this.colors[0] }, areaStyle: { opacity: 0.1 } }]
        };
      },
      error: (err) => console.error('Erro ao carregar dados do dashboard comercial:', err)
    });
  }
}
