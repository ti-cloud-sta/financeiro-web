import { Component, OnInit, effect, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CardComponent } from '../../shared/components/card/card.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { NgSelectModule } from '@ng-select/ng-select';
import { NgxEchartsDirective } from 'ngx-echarts';
import * as echarts from 'echarts';
import { EChartsOption } from 'echarts';
import { HttpClient } from '@angular/common/http';

import { ColaboradoresService, Colaborador } from '../../core/services/colaboradores.service';
import { CategoriasService, Categoria } from '../../core/services/categorias.service';
import { CargosColaboradoresService, CargoColaborador } from '../../core/services/cargos-colaboradores.service';

import { CentrosCustoService, CentroCusto } from '../../core/services/centros-custo.service';
import { UnidadesService, Unidade } from '../../core/services/unidades.service';
import { ImportacoesService, Importacao, DespesaExtraida } from '../../core/services/importacoes.service';
import { DespesasViagensService } from '../../core/services/despesas-viagens.service';
import { EmpresasService, Empresa } from '../../core/services/empresas.service';
import { IAuthService } from '../../core/interfaces/auth.service';
import { ViewChild, ElementRef, HostListener } from '@angular/core';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';
import { FlatpickrModule } from 'angularx-flatpickr';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { ThemeService } from '../../core/services/theme.service';
import { ToastService } from '../../core/services/toast.service';
import { RelatorioViagensComponent } from './relatorio-viagens/relatorio-viagens.component';

@Component({
  selector: 'app-despesas-viagens',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, NgSelectModule, CardComponent, ButtonComponent, BadgeComponent, ModalComponent, ConfirmModalComponent, NgxEchartsDirective, FlatpickrModule, SkeletonComponent, LoadingComponent, RelatorioViagensComponent],
  templateUrl: './despesas-viagens.component.html',
  styleUrl: './despesas-viagens.component.scss'
})
export class DespesasViagensComponent implements OnInit {
  isDashboardLoading = false;
  sidebarTab = signal<'dashboard' | 'relatorio' | 'atualizacao' | 'configuracoes'>('dashboard');
  activeDashboardTab = signal<'visao-geral' | 'categorias' | 'comercial-marketing'>('visao-geral');

  isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') !== null
    ? localStorage.getItem('sidebarCollapsed') === 'true'
    : true;

  toggleSidebar(): void {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  // Dashboard Refs & Status
  @ViewChild('dashboardWrapper') dashboardWrapper!: ElementRef;
  @ViewChild('dashboardContent') dashboardContent!: ElementRef;
  isFullscreen = false;

  @HostListener('document:fullscreenchange', ['$event'])
  @HostListener('document:webkitfullscreenchange', ['$event'])
  @HostListener('document:mozfullscreenchange', ['$event'])
  @HostListener('document:MSFullscreenChange', ['$event'])
  onFullscreenChange() {
    this.isFullscreen = !!document.fullscreenElement;
  }

  // Filtros Dashboard
  locale = Portuguese;

  dashDataInicio: Date | null = null;
  dashDataFim: Date | null = null;
  activePeriodShortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado' | null = null;

  dashFiltroEmpresa: string = null as any;
  dashFiltroPessoa: string = null as any;
  dashFiltroCategoria: string = null as any;

  // KPIs da aba Categorias
  topCategoryName = 'N/A';
  topCategoryValue = 0;
  maiorCrescimentoName = 'N/A';
  maiorCrescimentoPct = 0;

  // Seleção e interatividade de categorias
  selectedCategoryName: string | null = null;
  selectedCategoryId: number | null = null;
  categoryDetailsLoading = false;

  categoryVisaoGeral = {
    total: 0,
    quantidadeDespesas: 0,
    ticketMedio: 0,
    maiorDespesa: 0,
    maiorDespesaContexto: ''
  };
  categoryTabelaDespesas: any[] = [];
  categorySpenders: any[] = [];
  categoryEmpresasOption: EChartsOption = {};

  chartOptionAreaCategorias: EChartsOption = {};
  chartOptionDonutCategoriaTab: EChartsOption = {};
  donutCategoriasTab: any[] = [];

  dashVisaoGeral = {
    total: 0,
    quantidadeDespesas: 0,
    totalMes: 0,
    percentualMes: 0,
    ticketMedio: 0,
    ticketMedioPercentual: 0,
    maiorDespesa: 0,
    maiorDespesaContexto: 'Sem registros'
  };

  chartOptionArea: EChartsOption = {};
  chartOptionDonutCategoria: EChartsOption = {};
  chartOptionDonutEmpresa: EChartsOption = {};
  chartOptionMapa: EChartsOption = {};

  tabelaMaioresDespesas: any[] = [];

  themeService = inject(ThemeService);
  toastService = inject(ToastService);

  getThemeColors() {
    const isDark = this.themeService.activeTheme() === 'dark';
    return {
      text: isDark ? '#cbd5e1' : '#64748b',
      title: isDark ? '#f8fafc' : '#334155',
      border: isDark ? '#334155' : '#cbd5e1',
      borderLight: isDark ? '#0ea5e9' : '#f1f5f9',
      pieBorderColor: isDark ? '#014f75' : '#fff'
    };
  }

  constructor(
    private http: HttpClient,
    private colaboradoresService: ColaboradoresService,
    private categoriasService: CategoriasService,
    private cargosService: CargosColaboradoresService,
    private centrosCustoService: CentrosCustoService,
    private unidadesService: UnidadesService,
    private importacoesService: ImportacoesService,
    private despesasViagensService: DespesasViagensService,
    private empresasService: EmpresasService,
    private authService: IAuthService
  ) {
    effect(() => {
      // Registrar dependência reativa do Signal do tema
      const theme = this.themeService.activeTheme();

      // Forçar atualização dos gráficos recreando suas opções
      if (this.sidebarTab() === 'dashboard') {
        this.carregarDadosDashboard();
        if (this.selectedCategoryId) {
          this.carregarDetalhesCategoria();
        }
        this.atualizarDadosAnalitico();
      }
    });
  }

  ngOnInit(): void {
    this._loadDraft();
    this.carregarImportacoes();
    this.carregarEmpresas();
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
    this.carregarCentrosCustoGeral();
    this.carregarUnidadesGeral();
    this.selecionarAtalhoPeriodo('este-ano');
    this.selecionarAtalhoPeriodoAnalitico('este-ano');
  }

  carregarDadosDashboard() {
    if (this.activeDashboardTab() !== 'visao-geral') return;

    this.isDashboardLoading = true;

    const filtros: any = {};
    if (this.dashDataInicio) filtros.data_inicio = this.formatDate(this.dashDataInicio);
    if (this.dashDataFim) filtros.data_fim = this.formatDate(this.dashDataFim);
    if (this.dashFiltroEmpresa) filtros.id_empresa = this.dashFiltroEmpresa;
    if (this.dashFiltroPessoa) filtros.id_colaborador = this.dashFiltroPessoa;
    if (this.dashFiltroCategoria) filtros.id_categoria = this.dashFiltroCategoria;

    this.despesasViagensService.obterDashboardVisaoGeral(filtros).subscribe({
      next: (res) => {
        this.dashVisaoGeral = res.dashVisaoGeral;
        this.tabelaMaioresDespesas = res.tabelaMaioresDespesas || [];

        // Categoria com Maior Gasto
        if (res.donutCategorias?.length > 0) {
          const maxCat = res.donutCategorias.reduce((a: any, b: any) => b.value > a.value ? b : a);
          this.topCategoryName = maxCat.name;
          this.topCategoryValue = maxCat.value;
        } else {
          this.topCategoryName = 'N/A';
          this.topCategoryValue = 0;
        }

        this.donutCategoriasTab = res.donutCategorias || [];

        const evolucaoMeses = res.evolucao?.meses || [];
        const evolucaoSeries = res.evolucao?.series || [];

        this.maiorCrescimentoName = 'N/A';
        this.maiorCrescimentoPct = 0;

        if (evolucaoSeries && evolucaoSeries.length > 0 && evolucaoMeses.length >= 2) {
            let maxGrowth = -Infinity;
            let bestCat = 'N/A';
            
            for (const s of evolucaoSeries) {
                const data = s.data || [];
                if (data.length >= 2) {
                    const current = data[data.length - 1];
                    const previous = data[data.length - 2];
                    
                    if (previous > 0) {
                        const growth = ((current - previous) / previous) * 100;
                        if (growth > maxGrowth) {
                            maxGrowth = growth;
                            bestCat = s.name;
                        }
                    } else if (current > 0) {
                        if (maxGrowth < 100) {
                            maxGrowth = 100;
                            bestCat = s.name;
                        }
                    }
                }
            }
            
            if (maxGrowth !== -Infinity) {
                this.maiorCrescimentoName = bestCat;
                this.maiorCrescimentoPct = Math.round(maxGrowth);
            }
        }

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899'];
        const themeColors = this.getThemeColors();
        const isDark = this.themeService.activeTheme() === 'dark';

        // 1. Área Chart (Evolução Mensal)
        const areaChartOption = {
          color: colors,
          tooltip: { trigger: 'axis', formatter: (params: any[]) =>
            params.map(p => `${p.seriesName}: R$ ${p.value?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`).join('<br/>')
          },
          legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: themeColors.text } },
          grid: { top: 30, left: 20, right: 20, bottom: 40, containLabel: true },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: evolucaoMeses,
            axisLabel: { color: themeColors.text, fontSize: 11 },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: themeColors.border } }
          },
          yAxis: {
            type: 'value',
            axisLabel: { formatter: (v: number) => 'R$ ' + v.toLocaleString('pt-BR'), color: themeColors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          series: evolucaoSeries.map((s: any) => ({
            name: s.name,
            type: 'line',
            stack: 'Total',
            areaStyle: { opacity: 0.25 },
            smooth: true,
            emphasis: { focus: 'series' },
            data: s.data
          }))
        };
        this.chartOptionArea = areaChartOption as EChartsOption;
        this.chartOptionAreaCategorias = areaChartOption as EChartsOption;

        // 2. Donut Categorias
        const donutCatOption = {
          color: colors,
          tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}<br/>R$ ${p.value?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} (${p.percent}%)` },
          legend: { show: false },
          series: [{
            type: 'pie',
            radius: ['40%', '65%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: themeColors.pieBorderColor, borderWidth: 2 },
            label: { show: true, position: 'outer', formatter: '{b}\n{d}%', fontSize: 10, color: themeColors.text },
            labelLine: { show: true, length: 8, length2: 8 },
            data: res.donutCategorias || []
          }]
        };
        this.chartOptionDonutCategoria = donutCatOption as EChartsOption;
        this.chartOptionDonutCategoriaTab = donutCatOption as EChartsOption;

        // 3. Donut Empresas
        this.chartOptionDonutEmpresa = {
          color: ['#06b6d4', '#8b5cf6', '#f43f5e', '#eab308', '#3b82f6'],
          tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}<br/>R$ ${p.value?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} (${p.percent}%)` },
          legend: { show: false },
          series: [{
            type: 'pie',
            radius: ['40%', '65%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: themeColors.pieBorderColor, borderWidth: 2 },
            label: { show: true, position: 'outer', formatter: '{b}\n{d}%', fontSize: 10, color: themeColors.text },
            labelLine: { show: true, length: 8, length2: 8 },
            data: res.donutEmpresas || []
          }]
        } as EChartsOption;

        this.isDashboardLoading = false;

        // 4. Mapa (carregado de forma independente, sem bloquear o restante)
        this.http.get('/maps/brazil.json').subscribe({
          next: (geoJson: any) => {
            echarts.registerMap('brazil', geoJson);
            const maxVal = Math.max(1000, ...(res.mapaData || []).map((d: any) => d.value));

            this.chartOptionMapa = {
              tooltip: {
                trigger: 'item',
                formatter: (params: any) => {
                  if (!params.value) return `${params.name}<br/>Sem despesas`;
                  return `${params.name}<br/>Total: R$ ${params.value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}<br/>Qtd: ${params.data?.qtd || 0} despesas`;
                }
              },
              visualMap: {
                min: 0,
                max: maxVal,
                text: ['Alto', 'Baixo'],
                realtime: false,
                calculable: true,
                textStyle: { color: themeColors.text },
                inRange: { color: isDark ? ['#172554', '#3b82f6', '#60a5fa'] : ['#eff6ff', '#3b82f6', '#1e3a8a'] }
              },
              series: [
                {
                  name: 'Despesas por Estado',
                  type: 'map',
                  map: 'brazil',
                  roam: true,
                  label: { show: false },
                  data: res.mapaData || []
                }
              ]
            } as EChartsOption;
          },
          error: () => { /* mapa opcional */ }
        });
      },
      error: (err) => {
        console.error('Erro ao carregar dados do dashboard', err);
        this.toastService.show(err?.error?.detail || 'Erro ao carregar o dashboard.', 'error');
        this.isDashboardLoading = false;
      }
    });
  }

  formatDate(date: Date): string {
    const d = new Date(date);
    let month = '' + (d.getMonth() + 1);
    let day = '' + d.getDate();
    const year = d.getFullYear();

    if (month.length < 2) month = '0' + month;
    if (day.length < 2) day = '0' + day;

    return [year, month, day].join('-');
  }

  setSidebarTab(tab: 'dashboard' | 'relatorio' | 'atualizacao' | 'configuracoes') {
    this.sidebarTab.set(tab);
  }

  setActiveDashboardTab(tab: 'visao-geral' | 'categorias' | 'comercial-marketing'): void {
    this.activeDashboardTab.set(tab);
  }

  // ==========================================
  // CONFIRM MODAL (GENERIC)
  // ==========================================
  isConfirmModalOpen = false;
  confirmTitle = 'Confirmar Exclusão';
  confirmMessage = 'Tem certeza que deseja excluir este registro?';
  isConfirmLoading = false;
  confirmCallback: (() => void) | null = null;

  openConfirmModal(title: string, message: string, callback: () => void) {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmCallback = callback;
    this.isConfirmModalOpen = true;
    this.isConfirmLoading = false;
  }

  closeConfirmModal() {
    this.isConfirmModalOpen = false;
    this.confirmCallback = null;
  }

  executeConfirm() {
    if (this.confirmCallback) {
      this.isConfirmLoading = true;
      this.confirmCallback();
    }
  }

  // ==========================================

  listaUnidadesGeral: Unidade[] = [];
  carregarUnidadesGeral() {
    this.unidadesService.listar(1, 1000).subscribe({
      next: (res) => {
        this.listaUnidadesGeral = (res.items || []).sort((a, b) => (a.descricao || '').localeCompare(b.descricao || ''));
      }
    });
  }

  listaColaboradoresGeral: Colaborador[] = [];
  carregarColaboradoresGeral() {
    this.colaboradoresService.listar(1, 2000).subscribe({
      next: (res) => this.listaColaboradoresGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  listaCategoriasGeral: Categoria[] = [];
  carregarCategoriasGeral() {
    this.categoriasService.listar(1, 1000).subscribe({
      next: (res) => this.listaCategoriasGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  listaEmpresasGeral: any[] = [];
  carregarEmpresasGeral() {
    this.empresasService.listar(1, 1000, '', 1).subscribe({
      next: (res) => this.listaEmpresasGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  // ==========================================
  // IMPORTAÇÕES
  // ==========================================

  listaImportacoes: any[] = [];
  totalImportacoes = 0;
  totalImportacaoPages = 1;
  currentImportacaoPage = 1;
  itemsImportacaoPerPage = 10;
  searchImportacaoTerm = '';
  isImportacoesLoading = false;


  carregarImportacoes() {
    this.isImportacoesLoading = true;
    this.importacoesService.listar(this.currentImportacaoPage, this.itemsImportacaoPerPage, this.searchImportacaoTerm, 'IA_DESPESAS').subscribe({
      next: (res: any) => {
        this.listaImportacoes = res.items;
        this.totalImportacoes = res.total;
        this.totalImportacaoPages = res.total_pages;
        this.isImportacoesLoading = false;
      },
      error: (err: any) => {
        this.isImportacoesLoading = false;
        this.toastService.show(err?.error?.detail || 'Erro ao carregar histórico de importações.', 'error');
      }
    });
  }

  onSearchImportacaoChange(term: string) {
    this.searchImportacaoTerm = term;
    this.currentImportacaoPage = 1;
    this.carregarImportacoes();
  }

  goToImportacaoPage(page: number) {
    if (page >= 1 && page <= this.totalImportacaoPages) {
      this.currentImportacaoPage = page;
      this.carregarImportacoes();
    }
  }

  reprocessarImportacao(importacao: any) {
    alert('Função de reprocessamento em desenvolvimento para a importação: ' + importacao.nomeArquivo);
  }


  confirmarExclusaoImportacao(id: number) {
    this.openConfirmModal(
      'Excluir Importação',
      'Tem certeza que deseja excluir esta importação? Isso apagará permanentemente todas as movimentações e despesas associadas a ela.',
      () => {
        this.importacoesService.excluir(id).subscribe({
          next: () => {
            this.closeConfirmModal();
            this.carregarImportacoes();
            this.carregarEmpresas();
            this.toastService.show('Importação excluída com sucesso.', 'success');
          },
          error: (err) => {
            this.isConfirmLoading = false;
            this.toastService.show(err?.error?.detail || 'Erro ao excluir a importação.', 'error');
          }
        });
      }
    );
  }

  empresas: any[] = [];
  carregarEmpresas() {
    this.empresasService.listar(1, 100, '', 1).subscribe({
      next: (res) => {
        this.empresas = res.items
          .filter((e: any) => e.tipo !== 'INVISIVEL')
          .map((e: any) => {
            // Mapeia alguns ícones baseados no nome da empresa por padrão visual
            let icon = 'fa-solid fa-building';
            const nomeLower = e.nome.toLowerCase();

            if (nomeLower.includes('cartão') || nomeLower.includes('bb')) icon = 'fa-solid fa-credit-card';
            else if (nomeLower.includes('kinto') || nomeLower.includes('localiza')) icon = 'fa-solid fa-car';
            else if (nomeLower.includes('onfly')) icon = 'fa-solid fa-plane-departure';
            else if (nomeLower.includes('dv') || nomeLower.includes('despesa')) icon = 'fa-solid fa-file-invoice-dollar';
            else if (nomeLower.includes('sem parar')) icon = 'fa-solid fa-road-barrier';
            else if (nomeLower.includes('tastur') || nomeLower.includes('viagem')) icon = 'fa-solid fa-ticket';

            return { ...e, icon };
          });
      },
      error: (err) => console.error('Erro ao carregar empresas', err)
    });
  }



  isImportModalOpen = false;
  empresaSelecionada: any = null;
  uploadState: 'idle' | 'processing' | 'done' = 'idle';
  currentProcessingStep = 0;
  processingSteps = [
    'Importando arquivo selecionado',
    'Inteligência Artificial analisando dados (pode levar alguns segundos)',
    'Interpretando resposta e formatando tabela',
    'Pronto para conferência'
  ];

  isManualEntry = false;

  openImportModal(empresa: any) {
    if (!this._loadDraft()) {
      this.isManualEntry = false;
      this.empresaSelecionada = empresa;
      this.isImportModalOpen = true;
      this.uploadState = 'idle';
      this.currentProcessingStep = 0;
      this.selectedFileName = '';
    }

    // Garantir que as listas estejam atualizadas com as configurações mais recentes
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
  }

  closeImportModal(reason?: string) {
    if (reason === 'cancel-button' || reason === 'x-button') {
      this._clearDraft();
    }
    this.isImportModalOpen = false;
  }

  private _saveDraft() {
    const draft = {
      despesasExtraidas: this.despesasExtraidas,
      empresaSelecionada: this.empresaSelecionada,
      selectedFileName: this.selectedFileName,
      isManualEntry: this.isManualEntry,
      uploadState: this.uploadState,
      isImportModalOpen: this.isImportModalOpen
    };
    try {
      const obfuscated = btoa(encodeURIComponent(JSON.stringify(draft)));
      sessionStorage.setItem('despesas_viagens_draft', obfuscated);
    } catch(e) {}
  }

  onEmpresaManualChange(empresa: any) {
    this.empresaSelecionada = empresa;
    // Update existing draft rows to reflect the new company if needed
    this.despesasExtraidas.forEach(d => d.empresa = empresa?.nome || 'Empresa Desconhecida');
    this._saveDraft();
  }

  private _clearDraft() {
    sessionStorage.removeItem('despesas_viagens_draft');
  }

  private _loadDraft(): boolean {
    const draftStr = sessionStorage.getItem('despesas_viagens_draft');
    if (draftStr) {
      try {
        const draft = JSON.parse(decodeURIComponent(atob(draftStr)));
        if (draft && draft.isImportModalOpen && draft.uploadState === 'done') {
          this.despesasExtraidas = draft.despesasExtraidas || [];
          this.empresaSelecionada = draft.empresaSelecionada;
          this.selectedFileName = draft.selectedFileName;
          this.isManualEntry = draft.isManualEntry;
          this.uploadState = draft.uploadState;
          this.isImportModalOpen = draft.isImportModalOpen;
          return true;
        }
      } catch (e) {
        console.error('Erro ao ler draft', e);
      }
    }
    return false;
  }

  openManualEntryModal() {
    if (!this._loadDraft()) {
      this.isManualEntry = true;
      this.empresaSelecionada = null;
      this.despesasExtraidas = [];
      this.selectedFileName = 'Lançamento Manual';
      this.uploadState = 'done';
      this.isImportModalOpen = true;
    }
    
    // Garantir que as listas estejam atualizadas
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
  }

  isSalvandoExtraidos = false;

  salvarExtraidos() {
    const desc = true; if (desc) return; // TODO: DESCONECTADO DO BACKEND ANTIGO
    if (this.despesasExtraidas.length === 0) return;

    this.isSalvandoExtraidos = true;
    const idUserLogado = this.authService.currentUser()?.iduser;
    
    this.importacoesService.salvarExtraidos(this.selectedFileName, this.despesasExtraidas, idUserLogado).subscribe({
      next: (res) => {
        this.isSalvandoExtraidos = false;
        this._clearDraft();
        this.closeImportModal();
        this.despesasExtraidas = [];
        this.selectedFileName = '';
        this.carregarImportacoes(); // Recarrega a tabela de historico
        // Como não temos um toast de sucesso global no momento, o modal se fechará e a grid atualizará.
      },
      error: (err) => {
        this.isSalvandoExtraidos = false;
        this.showErrorToast(err?.error?.detail || 'Erro ao salvar os dados. Verifique se todos os cadastros selecionados existem.');
      }
    });
  }

  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  despesasExtraidas: any[] = [];
  selectedFileName: string = '';

  // ESTADOS DO MODAL DE CONFERÊNCIA
  dataCompetencia = signal<string>(new Date().toISOString().split('T')[0]);
  searchDespesaTerm = signal<string>('');
  mostrarDivergenciaOnly = signal<boolean>(false);
  isAddingDespesa = signal<boolean>(false);
  editingRowIndex = signal<number | null>(null);

  editColaborador = signal<string>('');
  editCategoria = signal<string>('');
  editValor = signal<number>(0);

  newDespesaColaborador = signal<string>('');
  newDespesaCategoria = signal<string>('');
  newDespesaValor = signal<number>(0);

  get filteredParsedDespesas() {
    let list = this.despesasExtraidas;
    if (this.mostrarDivergenciaOnly()) {
      list = list.filter(d => !d.pessoa_encontrada || !d.categoria_encontrada);
    }
    const search = this.searchDespesaTerm().toLowerCase();
    if (search) {
      list = list.filter(d => 
        (d.colaborador && d.colaborador.toLowerCase().includes(search)) || 
        (d.categoria && d.categoria.toLowerCase().includes(search)) ||
        (d.codigo_rdv && d.codigo_rdv.toLowerCase().includes(search))
      );
    }
    return list;
  }

  get totalCategoriasExtraidas(): number {
    const cats = new Set(this.despesasExtraidas.map(d => d.categoria));
    return cats.size;
  }

  get totalPessoasExtraidas(): number {
    const pessoas = new Set(this.despesasExtraidas.map(d => d.colaborador));
    return pessoas.size;
  }

  get totalDespesasExtraidas(): number {
    return this.despesasExtraidas.reduce((acc, curr) => acc + (Number(curr.valor) || 0), 0);
  }

  hasColaborador(nome: string): boolean {
    return this.listaColaboradoresGeral.some(c => c.nome === nome);
  }

  hasEmpresa(nome: string): boolean {
    return this.listaEmpresasGeral.some(e => e.nome === nome);
  }

  hasCategoria(nome: string): boolean {
    return this.listaCategoriasGeral.some(c => c.nome === nome);
  }

  adicionarLinhaEmBranco() {
    this.despesasExtraidas = [...this.despesasExtraidas, {
      empresa: this.empresaSelecionada?.nome || 'Empresa Desconhecida',
      colaborador: '',
      categoria: '',
      valor: 0
    }];
    this._saveDraft();
  }

  removerLinha(index: number) {
    this.despesasExtraidas.splice(index, 1);
    this.despesasExtraidas = [...this.despesasExtraidas];
    this._saveDraft();
  }

  startEdit(index: number, despesa: any) {
    this.editingRowIndex.set(index);
    this.editColaborador.set(despesa.colaborador);
    this.editCategoria.set(despesa.categoria);
    this.editValor.set(despesa.valor);
  }

  cancelEdit() {
    this.editingRowIndex.set(null);
  }

  saveEdit(index: number) {
    this.despesasExtraidas[index].colaborador = this.editColaborador();
    this.despesasExtraidas[index].categoria = this.editCategoria();
    this.despesasExtraidas[index].valor = this.editValor();
    // Assuming edit means they fixed it manually
    this.despesasExtraidas[index].pessoa_encontrada = true; 
    this.despesasExtraidas[index].categoria_encontrada = true;
    this.despesasExtraidas = [...this.despesasExtraidas];
    this.editingRowIndex.set(null);
    this._saveDraft();
  }

  startAddDespesa() {
    this.isAddingDespesa.set(true);
    this.newDespesaColaborador.set('');
    this.newDespesaCategoria.set('');
    this.newDespesaValor.set(0);
  }

  cancelAddDespesa() {
    this.isAddingDespesa.set(false);
  }

  confirmAddDespesa() {
    if (!this.newDespesaColaborador() || !this.newDespesaCategoria()) return;
    this.despesasExtraidas.push({
      empresa: this.empresaSelecionada?.nome || '',
      colaborador: this.newDespesaColaborador(),
      categoria: this.newDespesaCategoria(),
      valor: this.newDespesaValor(),
      pessoa_encontrada: true,
      categoria_encontrada: true
    });
    this.despesasExtraidas = [...this.despesasExtraidas];
    this.isAddingDespesa.set(false);
    this._saveDraft();
  }

  onNewDespesaValorChange(event: any) {
    const val = parseFloat(event.target.value.replace(',', '.'));
    this.newDespesaValor.set(isNaN(val) ? 0 : val);
  }

  onEditValorChange(event: any) {
    const val = parseFloat(event.target.value.replace(',', '.'));
    this.editValor.set(isNaN(val) ? 0 : val);
  }

  isConfirmandoESalvando = false;

  confirmarESalvar() {
    if (this.despesasExtraidas.length === 0) return;
    if (this.isConfirmandoESalvando) return;

    this.isConfirmandoESalvando = true;
    const idUserLogado = this.authService.currentUser()?.iduser;

    const payload = {
      nomeArquivo: this.selectedFileName || 'Lançamento Manual',
      despesas: this.despesasExtraidas.map(d => ({
        empresa: d.empresa || '',
        colaborador: d.colaborador,
        colaborador_original: d.colaborador_original || d.colaborador,
        categoria: d.categoria,
        valor: d.valor,
        data: d.data || null,
        nroDocumento: d.nroDocumento || null
      })),
      idUserInc: idUserLogado,
      dataCompetencia: this.dataCompetencia(),
      isManualEntry: this.isManualEntry,
      idEmpresaManual: this.isManualEntry ? (this.empresaSelecionada?.idEmpresas || null) : null
    };

    this.despesasViagensService.confirmarDespesas(payload).subscribe({
      next: (res: any) => {
        this.isConfirmandoESalvando = false;
        this._clearDraft();
        this.closeImportModal('confirm-success');
        this.despesasExtraidas = [];
        this.selectedFileName = '';
        this.carregarImportacoes();
        this.toastService.show(`${res.totalMovimentacoes} despesa(s) salva(s) com sucesso!`, 'success');
      },
      error: (err: any) => {
        this.isConfirmandoESalvando = false;
        this.toastService.show(err?.error?.detail || 'Erro ao salvar as despesas. Verifique os dados e tente novamente.', 'error');
      }
    });
  }

  selectedFile: File | null = null;

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFileName = file.name;
      this.selectedFile = file;
    } else {
      this.selectedFileName = '';
      this.selectedFile = null;
    }
  }

  toastMessage: string | null = null;
  showErrorToast(msg: string) {
    this.toastMessage = msg;
    setTimeout(() => this.toastMessage = null, 5000);
  }

  iniciarProcessamento() {
    if (!this.selectedFile) {
      this.showErrorToast("Por favor, selecione um arquivo primeiro.");
      return;
    }

    const file = this.selectedFile;
    this.uploadState = 'processing';
    this.currentProcessingStep = 0;

    // Passo 0 para Passo 1
    setTimeout(() => {
      this.currentProcessingStep = 1;

      const nomeEmpresa = this.empresaSelecionada?.nome || 'Empresa Desconhecida';
      this.despesasViagensService.processarArquivo(file, nomeEmpresa).subscribe({
        next: (res: any) => {
          console.log("[PROCESSAMENTO DESPESAS VIAGENS] Sucesso:", res);
          if (res && Array.isArray(res.dados)) {
            this.despesasExtraidas = res.dados.map((d: any) => ({
              ...d,
              empresa: nomeEmpresa,
              nroDocumento: d.codigo_rdv || d.nroDocumento || null,
              colaborador_original: d.colaborador // keep original name for alias
            }));
          } else if (res && Array.isArray(res.despesas)) {
            this.despesasExtraidas = res.despesas.map((d: any) => ({
              ...d,
              empresa: nomeEmpresa,
              nroDocumento: d.codigo_rdv || d.nroDocumento || null,
              colaborador_original: d.colaborador
            }));
          } else if (res && Array.isArray(res)) {
            this.despesasExtraidas = res.map((d: any) => ({
              ...d,
              empresa: nomeEmpresa,
              nroDocumento: d.codigo_rdv || d.nroDocumento || null,
              colaborador_original: d.colaborador
            }));
          }
          this.uploadState = 'done'; 
          this._saveDraft();
        },
        error: (err) => {
          console.error("[PROCESSAMENTO DESPESAS VIAGENS] Erro:", err);
          this.showErrorToast(err?.error?.detail || 'Erro ao processar o arquivo.');
          this.uploadState = 'idle';
        }
      });
    }, 600);
  }

  // ==========================================
  // ABA COMERCIAL/MARKETING — DADOS E GRÁFICOS
  // ==========================================

  // Filtros Comercial/Marketing
  analiticoDataInicio: Date | null = null;
  analiticoDataFim: Date | null = null;
  analiticoPeriodShortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado' | null = null;
  analiticoCategoria: string | null = null;
  analiticoColaborador: string | null = null;
  analiticoCentroCusto: string | null = null;
  isAnaliticoDetalhesActive = false;

  toggleAnaliticoDetalhes() {
    this.isAnaliticoDetalhesActive = !this.isAnaliticoDetalhesActive;
  }

  analiticoRankingTab: 'colaboradores' | 'categorias' = 'colaboradores';
  rankingColaboradores: { posicao: number, nome: string, valor: number, pct: number }[] = [];
  rankingCategorias: { posicao: number, nome: string, valor: number, pct: number }[] = [];

  setAnaliticoRankingTab(tab: 'colaboradores' | 'categorias') {
    this.analiticoRankingTab = tab;
  }

  // Detalhes Matrix Grid
  searchDetalhesTerm = '';
  detalhesCategoriasColunas: string[] = [];
  detalhesMatrizOriginal: { colaboradorNome: string, valoresPorCategoria: { [cat: string]: number }, total: number }[] = [];
  detalhesMatrizFiltrada: { colaboradorNome: string, valoresPorCategoria: { [cat: string]: number }, total: number }[] = [];
  detalhesTotaisPorCategoria: { [cat: string]: number } = {};
  detalhesTotalGeral = 0;

  onSearchDetalhesChange(term: string) {
    this.searchDetalhesTerm = term;
    this.filtrarDetalhesMatriz();
  }

  filtrarDetalhesMatriz() {
    if (!this.searchDetalhesTerm || !this.searchDetalhesTerm.trim()) {
      this.detalhesMatrizFiltrada = [...this.detalhesMatrizOriginal];
      return;
    }
    const term = this.searchDetalhesTerm.toLowerCase().trim();
    this.detalhesMatrizFiltrada = this.detalhesMatrizOriginal.filter(item =>
      item.colaboradorNome.toLowerCase().includes(term) ||
      item.total.toString().includes(term)
    );
  }

  // KPI
  analiticoTotalDespesas = 0;

  // Charts
  chartAnaliticoBarrasVerticais: EChartsOption = {};
  chartAnaliticoCategoriaBarras: EChartsOption = {};
  chartAnaliticoCategoriaDonut: EChartsOption = {};
  chartAnaliticoButterfly: EChartsOption = {};
  chartAnaliticoEvolucaoLinha: EChartsOption = {};
  chartAnaliticoCentroCusto: EChartsOption = {};
  chartAnaliticoMapa: EChartsOption = {};

  onAnaliticoDataInicioChange() {
    if (this.analiticoDataInicio && this.analiticoDataFim && this.analiticoDataInicio > this.analiticoDataFim) {
      this.analiticoDataFim = this.analiticoDataInicio;
    }
    this.analiticoPeriodShortcut = 'personalizado';
    this.atualizarDadosAnalitico();
  }

  onAnaliticoDataFimChange() {
    this.analiticoPeriodShortcut = 'personalizado';
    this.atualizarDadosAnalitico();
  }

  onAnaliticoShortcutSelectChange(val: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado') {
    if (val && val !== 'personalizado') {
      this.selecionarAtalhoPeriodoAnalitico(val);
    }
  }

  selecionarAtalhoPeriodoAnalitico(shortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado') {
    const today = new Date();
    const getPastDate = (monthsAgo: number) => {
      const d = new Date();
      d.setMonth(d.getMonth() - monthsAgo);
      return d;
    };

    if (shortcut === 'ultimo-bimestre') {
      this.analiticoDataInicio = getPastDate(2);
      this.analiticoDataFim = today;
    } else if (shortcut === 'ultimo-semestre') {
      this.analiticoDataInicio = getPastDate(6);
      this.analiticoDataFim = today;
    } else if (shortcut === 'este-ano') {
      this.analiticoDataInicio = new Date(today.getFullYear(), 0, 1);
      this.analiticoDataFim = new Date(today.getFullYear(), 11, 31);
    } else if (shortcut === 'ano-passado') {
      this.analiticoDataInicio = new Date(today.getFullYear() - 1, 0, 1);
      this.analiticoDataFim = new Date(today.getFullYear() - 1, 11, 31);
    }

    this.analiticoPeriodShortcut = shortcut;
    this.atualizarDadosAnalitico();
  }




  // --- Comercial/Marketing ---
  isAnaliticoLoading = false;
  analiticoDetalhes: any[] = [];


  atualizarDadosAnalitico() {
    this.isAnaliticoLoading = false;
    if (!this.activeDashboardTab() || this.activeDashboardTab() !== 'comercial-marketing') return;
    this.isAnaliticoLoading = true;

    const filtros: any = {
      data_inicio: this.analiticoDataInicio ? this.analiticoDataInicio.toISOString().split('T')[0] : null,
      data_fim: this.analiticoDataFim ? this.analiticoDataFim.toISOString().split('T')[0] : null,
      id_empresa: null,
      id_colaborador: this.analiticoColaborador || null,
      id_categoria: this.analiticoCategoria || null,
      tipo_importacao: 'IA_DESPESAS'
    };

    this.despesasViagensService.obterVisaoComercial(filtros).subscribe({
      next: (dados) => {
        this.isAnaliticoLoading = false;
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899', '#06b6d4', '#8b5cf6', '#f43f5e'];
        const themeColors = this.getThemeColors();
        const isDark = this.themeService.activeTheme() === 'dark';

        this.analiticoTotalDespesas = dados.analiticoTotalDespesas;

        // 3. Barras verticais
        this.chartAnaliticoBarrasVerticais = {
          color: [colors[0]],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              const p = params[0];
              return `${p.name}<br/>Total: ${p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
            }
          },
          grid: { top: 30, left: 20, right: 20, bottom: 30, containLabel: true },
          xAxis: {
            type: 'category',
            data: dados.meses,
            axisLabel: { fontSize: 11, color: themeColors.text },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: themeColors.border } }
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: (val: number) => val >= 1000 ? `R$ ${(val / 1000).toFixed(0)}k` : `R$ ${val}`,
              fontSize: 11,
              color: themeColors.text
            },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          series: [{
            name: 'Total',
            type: 'bar',
            barWidth: '50%',
            itemStyle: { borderRadius: [4, 4, 0, 0] },
            data: dados.barrasVerticais
          }]
        };

        // 4. Barras horizontais categorias e 5. Donut
        const catNames = dados.categoriaBarras.map((c: any) => c.name);
        const catNamesAsc = [...catNames].reverse();
        const catValuesAsc = dados.categoriaBarras.map((c: any) => c.value).reverse();

        this.chartAnaliticoCategoriaBarras = {
          color: colors,
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              const p = params[0];
              return `${p.name}<br/>Total: ${p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
            }
          },
          grid: { top: 10, left: 10, right: 80, bottom: 10, containLabel: true },
          xAxis: { type: 'value', axisLabel: { show: false }, splitLine: { show: false } },
          yAxis: {
            type: 'category',
            data: catNamesAsc,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { fontSize: 11, color: themeColors.text, width: 120, overflow: 'truncate' }
          },
          series: [{
            name: 'Valor',
            type: 'bar',
            barWidth: '60%',
            itemStyle: { borderRadius: [0, 4, 4, 0] },
            label: {
              show: true,
              position: 'right',
              formatter: (params: any) => params.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
              fontSize: 10,
              color: themeColors.text
            },
            data: catValuesAsc.map((v: any, i: number) => ({ value: v, itemStyle: { color: colors[i % colors.length] } }))
          }]
        };

        this.chartAnaliticoCategoriaDonut = {
          color: colors,
          tooltip: { trigger: 'item', formatter: '{b}: R$ {c} ({d}%)' },
          legend: { show: false },
          series: [{
            type: 'pie',
            radius: ['40%', '65%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: themeColors.pieBorderColor, borderWidth: 2 },
            label: {
              show: true,
              position: 'outer',
              formatter: '{b}\n{d}%',
              fontSize: 10,
              color: themeColors.text
            },
            labelLine: { show: true, length: 8, length2: 8 },
            data: dados.categoriaBarras
          }]
        };

        // 5.b Butterfly Chart (Comercial vs Marketing por Categoria)
        const bf = dados.butterfly;
        const butterflyCats = bf.categorias;
        const comValues = bf.comercial.map((v: number) => -v);
        const mktValues = bf.marketing;

        this.chartAnaliticoButterfly = {
          color: ['#3b82f6', '#ec4899'],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              let res = `<strong>${params[0].name}</strong><br/>`;
              params.forEach((p: any) => {
                const val = Math.abs(p.value);
                res += `${p.marker} ${p.seriesName}: ${val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}<br/>`;
              });
              return res;
            }
          },
          legend: {
            data: ['Comercial', 'Marketing'],
            top: 0,
            textStyle: { fontSize: 11, color: themeColors.text }
          },
          grid: { top: 30, left: 10, right: 10, bottom: 10, containLabel: true },
          xAxis: {
            type: 'value',
            axisLabel: {
              formatter: (val: number) => {
                const abs = Math.abs(val);
                return abs >= 1000 ? `R$ ${(abs / 1000).toFixed(0)}k` : `R$ ${abs}`;
              },
              fontSize: 9,
              color: themeColors.text
            },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          yAxis: {
            type: 'category',
            data: butterflyCats,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { fontSize: 10, color: themeColors.text, width: 90, overflow: 'truncate' }
          },
          series: [
            {
              name: 'Comercial',
              type: 'bar',
              stack: 'total',
              itemStyle: { borderRadius: [4, 0, 0, 4] },
              data: comValues
            },
            {
              name: 'Marketing',
              type: 'bar',
              stack: 'total',
              itemStyle: { borderRadius: [0, 4, 4, 0] },
              data: mktValues
            }
          ]
        };

        // 6. Evolução Centro de Custo
        const evolSeries = dados.evolucaoCentroCusto.series.map((s: any, idx: number) => ({
          name: s.name,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2 },
          data: s.data,
          itemStyle: { color: colors[idx % colors.length] }
        }));

        this.chartAnaliticoEvolucaoLinha = {
          tooltip: {
            trigger: 'axis',
            formatter: (params: any) => {
              let res = `<strong>${params[0].name}</strong><br/>`;
              params.forEach((p: any) => {
                res += `${p.marker} ${p.seriesName}: ${p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}<br/>`;
              });
              return res;
            }
          },
          grid: { top: 30, left: 20, right: 20, bottom: 30, containLabel: true },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dados.evolucaoCentroCusto.meses,
            axisLabel: { fontSize: 11, color: themeColors.text },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: themeColors.border } }
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: (val: number) => val >= 1000 ? `R$ ${(val / 1000).toFixed(0)}k` : `R$ ${val}`,
              fontSize: 11,
              color: themeColors.text
            },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          series: evolSeries
        };

        // 7. Barras horizontais centro de custo
        const ccNamesAsc = [...dados.centroCustoBarras].reverse().map((c: any) => c.name);
        const ccValuesAsc = [...dados.centroCustoBarras].reverse().map((c: any) => c.value);

        this.chartAnaliticoCentroCusto = {
          color: ['#6366f1'],
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              const p = params[0];
              return `${p.name}<br/>Total: ${p.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
            }
          },
          grid: { top: 10, left: 10, right: 80, bottom: 10, containLabel: true },
          xAxis: { type: 'value', axisLabel: { show: false }, splitLine: { show: false } },
          yAxis: {
            type: 'category',
            data: ccNamesAsc,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { fontSize: 10, color: themeColors.text, width: 180, overflow: 'truncate' }
          },
          series: [{
            name: 'Valor',
            type: 'bar',
            barWidth: '55%',
            itemStyle: { borderRadius: [0, 4, 4, 0], color: '#6366f1' },
            label: {
              show: true,
              position: 'right',
              formatter: (params: any) => params.value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
              fontSize: 10,
              color: themeColors.text
            },
            data: ccValuesAsc
          }]
        };

        // 8. Mapa
        const maxMapVal = Math.max(1000, ...dados.mapaData.map((d: any) => d.value));
        const totalGeral = dados.analiticoTotalDespesas || 1;
        const mapaDataFormatado = dados.mapaData.map((d: any) => ({
          ...d,
          pct: ((d.value / totalGeral) * 100).toFixed(1)
        }));

        this.chartAnaliticoMapa = {
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
              const pct = params.data?.pct || '0.0';
              return `${params.name}<br/>Total: ${(params.value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}<br/>Participação: ${pct}%`;
            }
          },
          visualMap: {
            min: 0,
            max: maxMapVal,
            text: ['Alto', 'Baixo'],
            realtime: false,
            calculable: true,
            textStyle: { color: themeColors.text },
            inRange: { color: isDark ? ['#172554', '#3b82f6', '#60a5fa'] : ['#eff6ff', '#3b82f6', '#1e3a8a'] }
          },
          series: [{
            name: 'Despesas por Estado',
            type: 'map',
            map: 'brazil',
            roam: true,
            label: { show: false },
            data: mapaDataFormatado
          }]
        };

        // 9-11. Outros paineis
        this.rankingColaboradores = dados.rankingColaboradores;
        this.rankingCategorias = dados.rankingCategorias;
        this.detalhesMatrizOriginal = dados.detalhesMatrizOriginal;
        this.detalhesCategoriasColunas = dados.detalhesCategoriasColunas;
        this.detalhesTotaisPorCategoria = dados.detalhesTotaisPorCategoria;
        this.detalhesTotalGeral = dados.detalhesTotalGeral;

        // Atribuir detalhes lista
        this.analiticoDetalhes = dados.detalhes;

        this.filtrarDetalhesMatriz();
      },
      error: (err) => {
        console.error("Erro ao carregar dados analíticos", err);
        this.isAnaliticoLoading = false;
      }
    });
  }



  toggleFullscreen() {
    const elem = this.dashboardWrapper?.nativeElement;

    if (!document.fullscreenElement) {
      if (elem?.requestFullscreen) {
        elem.requestFullscreen().catch((err: any) => {
          console.error(`Erro ao tentar entrar em modo tela cheia: ${err.message}`);
        });
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }

  onDataInicioChange() {
    if (this.dashDataInicio && this.dashDataFim && this.dashDataInicio > this.dashDataFim) {
      this.dashDataFim = this.dashDataInicio;
    }
    this.activePeriodShortcut = 'personalizado';
    if (this.isPeriodoValido()) {
      this.carregarDadosDashboard();
    }
  }

  onDataFimChange() {
    this.activePeriodShortcut = 'personalizado';
    if (this.isPeriodoValido()) {
      this.carregarDadosDashboard();
    }
  }

  onShortcutSelectChange(val: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado') {
    if (val && val !== 'personalizado') {
      this.selecionarAtalhoPeriodo(val);
    }
  }

  isPeriodoValido(): boolean {
    if (!this.dashDataInicio && !this.dashDataFim) {
      return true;
    }
    return !!this.dashDataInicio && !!this.dashDataFim && this.dashDataInicio <= this.dashDataFim;
  }

  selecionarAtalhoPeriodo(shortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado') {
    const today = new Date();

    const getPastDate = (monthsAgo: number) => {
      const d = new Date();
      d.setMonth(d.getMonth() - monthsAgo);
      return d;
    };

    if (shortcut === 'ultimo-bimestre') {
      this.dashDataInicio = getPastDate(2);
      this.dashDataFim = today;
    } else if (shortcut === 'ultimo-semestre') {
      this.dashDataInicio = getPastDate(6);
      this.dashDataFim = today;
    } else if (shortcut === 'este-ano') {
      this.dashDataInicio = new Date(today.getFullYear(), 0, 1);
      this.dashDataFim = new Date(today.getFullYear(), 11, 31);
    } else if (shortcut === 'ano-passado') {
      this.dashDataInicio = new Date(today.getFullYear() - 1, 0, 1);
      this.dashDataFim = new Date(today.getFullYear() - 1, 11, 31);
    }

    this.activePeriodShortcut = shortcut;
    this.carregarDadosDashboard();
  }

  selecionarCategoria(name: string, id: number) {
    if (this.selectedCategoryId === id) {
      this.selectedCategoryName = null;
      this.selectedCategoryId = null;
    } else {
      this.selectedCategoryName = name;
      this.selectedCategoryId = id;
      this.carregarDetalhesCategoria();
    }
  }

  carregarDetalhesCategoria() {
    this.categoryDetailsLoading = false;
    if (!this.selectedCategoryId) return;

    this.categoryDetailsLoading = true;

    const filtros: any = {
      id_categoria: this.selectedCategoryId
    };
    if (this.dashDataInicio) {
      filtros.data_inicio = this.formatDate(this.dashDataInicio);
    }
    if (this.dashDataFim) {
      filtros.data_fim = this.formatDate(this.dashDataFim);
    }
    if (this.dashFiltroEmpresa) {
      filtros.id_empresa = this.dashFiltroEmpresa;
    }
    if (this.dashFiltroPessoa) {
      filtros.id_colaborador = this.dashFiltroPessoa;
    }

    this.despesasViagensService.obterDashboardVisaoGeral(filtros).subscribe({
      next: (res) => {
        this.categoryVisaoGeral = {
          total: res.dashVisaoGeral?.total || 0,
          quantidadeDespesas: res.dashVisaoGeral?.quantidadeDespesas || 0,
          ticketMedio: res.dashVisaoGeral?.ticketMedio || 0,
          maiorDespesa: res.dashVisaoGeral?.maiorDespesa || 0,
          maiorDespesaContexto: res.dashVisaoGeral?.maiorDespesaContexto || 'N/A'
        };
        this.categoryTabelaDespesas = res.tabelaMaioresDespesas || [];
        this.categorySpenders = res.spenders || [];

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899'];
        const themeColors = this.getThemeColors();
        this.categoryEmpresasOption = {
          color: colors,
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { top: 20, left: 10, right: 20, bottom: 20, containLabel: true },
          xAxis: { type: 'value', axisLabel: { show: false }, splitLine: { show: false } },
          yAxis: {
            type: 'category',
            data: (res.donutEmpresas || []).map((e: any) => e.name),
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: themeColors.text }
          },
          series: [
            {
              name: 'Valor',
              type: 'bar',
              barWidth: '60%',
              label: {
                show: true,
                position: 'right',
                formatter: (params: any) => {
                  const val = params.value;
                  return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
                },
                fontSize: 10,
                color: themeColors.text
              },
              data: (res.donutEmpresas || []).map((e: any) => e.value)
            }
          ]
        };

        this.categoryDetailsLoading = false;
        this.isDashboardLoading = false;
      },
      error: (err) => {
        console.error('Erro ao carregar detalhes da categoria', err);
        this.categoryDetailsLoading = false;
        this.isDashboardLoading = false;
      }
    });
  }

  listaCentrosCustoGeral: any[] = [];
  carregarCentrosCustoGeral() {
    this.centrosCustoService.listar(1, 1000).subscribe({
      next: (res) => {
        this.listaCentrosCustoGeral = (res.items || []).sort((a: any, b: any) => (a.nome || '').localeCompare(b.nome || ''));
      }
    });
  }

  async exportToPDF() {
    if (!this.dashboardContent) return;

    try {
      const element = this.dashboardContent.nativeElement;
      
      const computedStyle = getComputedStyle(document.documentElement);
      const bgCol = computedStyle.getPropertyValue('--color-bg').trim() || '#ffffff';

      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: bgCol,
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight,
        onclone: (clonedDoc) => {
          const stickyEls = clonedDoc.querySelectorAll('.sticky-col-left, .sticky-col-right');
          stickyEls.forEach((el: any) => {
            el.style.position = 'static';
          });
          
          const scrollEls = clonedDoc.querySelectorAll('.table-responsive');
          scrollEls.forEach((el: any) => {
            el.style.maxHeight = 'none';
            el.style.height = 'auto';
            el.style.overflow = 'hidden';
          });
        }
      });

      if (!canvas || canvas.width === 0 || canvas.height === 0) {
        throw new Error('A renderização retornou uma imagem vazia ou o elemento está oculto.');
      }

      const imgData = canvas.toDataURL('image/jpeg', 1.0);
      const pdf = new jsPDF('l', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      const pdfHeightPage = pdf.internal.pageSize.getHeight();

      pdf.setFillColor(bgCol);
      pdf.rect(0, 0, pdfWidth, pdfHeightPage, 'F');

      pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);
      pdf.save('dashboard-despesas-viagens.pdf');
    } catch (error: any) {
      console.error('Erro ao gerar PDF:', error);
      alert('Erro ao gerar PDF: ' + (error?.message || error));
    }
  }

}

