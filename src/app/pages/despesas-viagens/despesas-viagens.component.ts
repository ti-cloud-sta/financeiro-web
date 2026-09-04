import { Component, OnInit, effect, inject } from '@angular/core';
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
import { EmpresasService, Empresa } from '../../core/services/empresas.service';
import { IAuthService } from '../../core/interfaces/auth.service';
import { ViewChild, ElementRef, HostListener } from '@angular/core';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';
import { FlatpickrModule } from 'angularx-flatpickr';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-despesas-viagens',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, NgSelectModule, CardComponent, ButtonComponent, BadgeComponent, ModalComponent, ConfirmModalComponent, NgxEchartsDirective, FlatpickrModule, SkeletonComponent],
  templateUrl: './despesas-viagens.component.html',
  styleUrl: './despesas-viagens.component.scss'
})
export class DespesasViagensComponent implements OnInit {
  isDashboardLoading = false;
  activeTab: 'dashboard' | 'atualizacao' | 'configuracoes' = 'dashboard';
  activeDashboardTab: 'visao-geral' | 'categorias' | 'comercial-marketing' | 'relatorio' = 'visao-geral';

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
    private empresasService: EmpresasService,
    private authService: IAuthService
  ) {
    effect(() => {
      // Registrar dependência reativa do Signal do tema
      const theme = this.themeService.activeTheme();

      // Forçar atualização dos gráficos recreando suas opções
      if (this.activeTab === 'dashboard') {
        this.carregarDadosDashboard();
        if (this.selectedCategoryId) {
          this.carregarDetalhesCategoria();
        }
        this.atualizarDadosAnalitico();
        this.atualizarDadosRelatorio();
      }
    });
  }

  ngOnInit(): void {
    this.carregarImportacoes();
    this.carregarEmpresas();
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
    this.carregarCentrosCustoGeral();
    this.carregarUnidadesGeral();
    this.selecionarAtalhoPeriodo('este-ano');
    this.selecionarAtalhoPeriodoAnalitico('este-ano');
    this.selecionarAtalhoPeriodoRelatorio('este-ano');
  }

  carregarDadosDashboard() {
    this.isDashboardLoading = true;
    const filtros: any = {};
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
    if (this.dashFiltroCategoria) {
      filtros.id_categoria = this.dashFiltroCategoria;
    }
    
    filtros.tipo_importacao = 'IA_DESPESAS';

    this.importacoesService.obterDadosDashboard(filtros).subscribe({
      next: (res) => {
        this.dashVisaoGeral = res.dashVisaoGeral;
        this.tabelaMaioresDespesas = res.tabelaMaioresDespesas;
        this.donutCategoriasTab = res.donutCategorias || [];

        // Calcular Categoria com Maior Gasto
        if (res.donutCategorias && res.donutCategorias.length > 0) {
          let maxCat = res.donutCategorias[0];
          for (const cat of res.donutCategorias) {
            if (cat.value > maxCat.value) {
              maxCat = cat;
            }
          }
          this.topCategoryName = maxCat.name;
          this.topCategoryValue = maxCat.value;
        } else {
          this.topCategoryName = 'N/A';
          this.topCategoryValue = 0;
        }

        // Maior crescimento
        if (res.maiorCrescimento) {
          this.maiorCrescimentoName = res.maiorCrescimento.name || 'N/A';
          this.maiorCrescimentoPct = res.maiorCrescimento.percentage || 0;
        } else {
          this.maiorCrescimentoName = 'N/A';
          this.maiorCrescimentoPct = 0;
        }

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899'];
        const themeColors = this.getThemeColors();
        const isDark = this.themeService.activeTheme() === 'dark';

        // 1. Area Chart (Evolução)
        this.chartOptionArea = {
          color: colors,
          tooltip: { trigger: 'axis' },
          legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: themeColors.text } },
          grid: { top: 30, left: 20, right: 20, bottom: 40, containLabel: true },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: res.evolucao.meses,
            axisLabel: { color: themeColors.text, fontSize: 11 },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: themeColors.border } }
          },
          yAxis: {
            type: 'value',
            axisLabel: { formatter: 'R$ {value}', color: themeColors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          series: res.evolucao.series.map((s: any) => ({
            name: s.name,
            type: 'line',
            stack: 'Total',
            areaStyle: {},
            emphasis: { focus: 'series' },
            data: s.data
          }))
        };

        this.chartOptionAreaCategorias = {
          color: colors,
          tooltip: { trigger: 'axis' },
          legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: themeColors.text } },
          grid: { top: 30, left: 20, right: 20, bottom: 40, containLabel: true },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: res.evolucao.meses,
            axisLabel: { color: themeColors.text, fontSize: 11 },
            axisTick: { show: false },
            axisLine: { lineStyle: { color: themeColors.border } }
          },
          yAxis: {
            type: 'value',
            axisLabel: { formatter: 'R$ {value}', color: themeColors.text, fontSize: 11 },
            splitLine: { lineStyle: { color: themeColors.borderLight } }
          },
          series: res.evolucao.series.map((s: any) => ({
            name: s.name,
            type: 'line',
            stack: 'Total',
            areaStyle: {},
            emphasis: { focus: 'series' },
            data: s.data
          }))
        };

        // 2. Donut Categorias
        this.chartOptionDonutCategoria = {
          color: colors,
          tooltip: { trigger: 'item', formatter: '{b}: R$ {c} ({d}%)' },
          legend: { show: false },
          series: [
            {
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
              data: res.donutCategorias
            }
          ]
        };

        this.chartOptionDonutCategoriaTab = {
          color: colors,
          tooltip: { trigger: 'item', formatter: '{b}: R$ {c} ({d}%)' },
          legend: { show: false },
          series: [
            {
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
              data: res.donutCategorias
            }
          ]
        };

        // 3. Donut Empresas
        this.chartOptionDonutEmpresa = {
          color: ['#06b6d4', '#8b5cf6', '#f43f5e', '#eab308'],
          tooltip: { trigger: 'item', formatter: '{b}: R$ {c} ({d}%)' },
          legend: { show: false },
          series: [
            {
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
              data: res.donutEmpresas
            }
          ]
        };

        // 4. Map (chartOptionMapa)
        this.http.get('/maps/brazil.json').subscribe({
          next: (geoJson: any) => {
            echarts.registerMap('brazil', geoJson);

            const maxVal = Math.max(1000, ...res.mapaData.map((d: any) => d.value));

            this.chartOptionMapa = {
              tooltip: {
                trigger: 'item',
                formatter: (params: any) => {
                  return `${params.name}<br/>Total: R$ ${params.value || 0}<br/>Qtd: ${params.data?.qtd || 0} despesas`;
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
                  data: res.mapaData
                }
              ]
            };

            if (this.selectedCategoryId) {
              this.carregarDetalhesCategoria();
            } else {
              this.isDashboardLoading = false;
            }
          },
          error: (mapErr) => {
            console.error('Erro ao carregar mapa do Brasil', mapErr);
            this.isDashboardLoading = false;
          }
        });
      },
      error: (err) => {
        console.error('Erro ao carregar dados do dashboard', err);
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

  setActiveTab(tab: 'dashboard' | 'atualizacao' | 'configuracoes') {
    this.activeTab = tab;
  }

  setActiveDashboardTab(tab: 'visao-geral' | 'categorias' | 'comercial-marketing' | 'relatorio'): void {
    this.activeDashboardTab = tab;
    if (tab === 'relatorio') {
      this.atualizarDadosRelatorio();
    }
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

  carregarImportacoes() {
    this.importacoesService.listar(this.currentImportacaoPage, this.itemsImportacaoPerPage, this.searchImportacaoTerm, 'IA_DESPESAS').subscribe({
      next: (res: any) => {
        this.listaImportacoes = res.items;
        this.totalImportacoes = res.total;
        this.totalImportacaoPages = res.total_pages;
      },
      error: (err: any) => console.error('Erro ao carregar importacoes', err)
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
    this.openConfirmModal('Excluir Importação', 'Tem certeza que deseja excluir esta importação? Isso apagará permanentemente todas as movimentações e despesas associadas a ela.', () => {
      this.importacoesService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarImportacoes(); // Atualiza a grid
          this.carregarEmpresas(); // Atualiza os cards
        },
        error: (err) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }

  empresas: any[] = [];
  carregarEmpresas() {
    this.empresasService.listar(1, 100, '', 1).subscribe({
      next: (res) => {
        this.empresas = res.items.map(e => {
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

  openImportModal(empresa: any) {
    this.empresaSelecionada = empresa;
    this.isImportModalOpen = true;
    this.uploadState = 'idle';
    this.currentProcessingStep = 0;
    this.selectedFileName = '';

    // Garantir que as listas estejam atualizadas com as configurações mais recentes
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
  }

  closeImportModal() {
    this.isImportModalOpen = false;
  }

  isSalvandoExtraidos = false;

  salvarExtraidos() {
    if (this.despesasExtraidas.length === 0) return;

    this.isSalvandoExtraidos = true;
    const idUserLogado = this.authService.currentUser()?.iduser;
    
    this.importacoesService.salvarExtraidos(this.selectedFileName, this.despesasExtraidas, idUserLogado).subscribe({
      next: (res) => {
        this.isSalvandoExtraidos = false;
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
  despesasExtraidas: DespesaExtraida[] = [];
  selectedFileName: string = '';

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
  }

  removerLinha(index: number) {
    this.despesasExtraidas.splice(index, 1);
    this.despesasExtraidas = [...this.despesasExtraidas];
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
      this.importacoesService.analisarExtrato(file, nomeEmpresa).subscribe({
        next: (res) => {
          if (res.sucesso) {
            // Arredondando todos os valores retornados para 2 casas decimais e associando a empresa selecionada no card
            this.despesasExtraidas = res.dados.map((d: any) => ({
              ...d,
              empresa: this.empresaSelecionada?.nome || 'Empresa Desconhecida',
              valor: Number(parseFloat(d.valor).toFixed(2))
            }));

            this.currentProcessingStep = 2; // Interpretando...
            setTimeout(() => {
              this.currentProcessingStep = 3; // Pronto para conferência...
              setTimeout(() => {
                this.uploadState = 'done';
              }, 600);
            }, 600);
          } else {
            this.showErrorToast('Erro ao processar arquivo pela IA.');
            this.uploadState = 'idle';
          }
        },
        error: (err) => {
          console.error(err);
          this.showErrorToast(err?.error?.detail || 'Erro de conexão ou processamento com a IA. Tente novamente.');
          this.uploadState = 'idle';
        }
      });
    }, 500);
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
    this.isAnaliticoLoading = true;

    const filtros: any = {
      data_inicio: this.analiticoDataInicio ? this.analiticoDataInicio.toISOString().split('T')[0] : null,
      data_fim: this.analiticoDataFim ? this.analiticoDataFim.toISOString().split('T')[0] : null,
      id_empresa: null,
      id_colaborador: this.analiticoColaborador || null,
      id_categoria: this.analiticoCategoria || null,
      tipo_importacao: 'IA_DESPESAS'
    };

    this.importacoesService.obterDadosDashboardAnalitico(filtros).subscribe({
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

  // ==========================================
  // ABA RELATÓRIO — GRID E FILTROS
  // ==========================================

  // Filtros Relatório
  relatorioDataInicio: Date | null = null;
  relatorioDataFim: Date | null = null;
  relatorioPeriodShortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado' | null = 'este-ano';
  relatorioEmpresa: number | null = null;
  relatorioColaborador: number | null = null;
  relatorioCentroCusto: string | null = null;

  isRelatorioLoading = false;
  relatorioDetalhesMatrizOriginal: any[] = [];
  relatorioDetalhesMatrizFiltrada: any[] = [];
  relatorioDetalhesCategoriasColunas: string[] = [];
  relatorioDetalhesTotaisPorCategoria: { [cat: string]: number } = {};
  relatorioDetalhesTotalGeral = 0;
  searchRelatorioTerm = '';

  onSearchRelatorioChange(term: string) {
    this.searchRelatorioTerm = term;
    this.filtrarRelatorioDetalhesMatriz();
  }

  filtrarRelatorioDetalhesMatriz() {
    if (!this.searchRelatorioTerm || !this.searchRelatorioTerm.trim()) {
      this.relatorioDetalhesMatrizFiltrada = [...this.relatorioDetalhesMatrizOriginal];
      return;
    }
    const term = this.searchRelatorioTerm.toLowerCase().trim();
    this.relatorioDetalhesMatrizFiltrada = this.relatorioDetalhesMatrizOriginal.filter(item =>
      item.colaboradorNome.toLowerCase().includes(term) ||
      (item.empresaNome && item.empresaNome.toLowerCase().includes(term)) ||
      item.total.toString().includes(term)
    );
  }

  onRelatorioDataInicioChange() {
    if (this.relatorioDataInicio && this.relatorioDataFim && this.relatorioDataInicio > this.relatorioDataFim) {
      this.relatorioDataFim = this.relatorioDataInicio;
    }
    this.relatorioPeriodShortcut = 'personalizado';
    this.atualizarDadosRelatorio();
  }

  onRelatorioDataFimChange() {
    this.relatorioPeriodShortcut = 'personalizado';
    this.atualizarDadosRelatorio();
  }

  onRelatorioShortcutSelectChange(val: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'personalizado') {
    if (val !== 'personalizado') {
      this.selecionarAtalhoPeriodoRelatorio(val);
    }
  }

  selecionarAtalhoPeriodoRelatorio(shortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado') {
    const today = new Date();
    const getPastDate = (months: number) => {
      const d = new Date();
      d.setMonth(d.getMonth() - months);
      return d;
    };

    switch (shortcut) {
      case 'ultimo-bimestre':
        this.relatorioDataInicio = getPastDate(2);
        this.relatorioDataFim = today;
        break;
      case 'ultimo-semestre':
        this.relatorioDataInicio = getPastDate(6);
        this.relatorioDataFim = today;
        break;
      case 'este-ano':
        this.relatorioDataInicio = new Date(today.getFullYear(), 0, 1);
        this.relatorioDataFim = new Date(today.getFullYear(), 11, 31);
        break;
      case 'ano-passado':
        this.relatorioDataInicio = new Date(today.getFullYear() - 1, 0, 1);
        this.relatorioDataFim = new Date(today.getFullYear() - 1, 11, 31);
        break;
    }
    this.relatorioPeriodShortcut = shortcut;
    this.atualizarDadosRelatorio();
  }

  atualizarDadosRelatorio() {
    this.isRelatorioLoading = true;
    const filtros: any = {
      data_inicio: this.relatorioDataInicio ? this.relatorioDataInicio.toISOString().split('T')[0] : null,
      data_fim: this.relatorioDataFim ? this.relatorioDataFim.toISOString().split('T')[0] : null,
      id_empresa: this.relatorioEmpresa || null,
      id_colaborador: this.relatorioColaborador || null,
      id_categoria: null,
      tipo_importacao: 'IA_DESPESAS'
    };

    this.importacoesService.obterDadosDashboardAnalitico(filtros).subscribe({
      next: (dados) => {
        this.isRelatorioLoading = false;
        
        let matriz = dados.detalhesMatrizOriginal || [];
        
        // Filtro local de Centro de Custo na matriz
        if (this.relatorioCentroCusto) {
          const colabCCMap = new Map<string, string>();
          (dados.detalhes || []).forEach((item: any) => {
            if (item.colaboradorNome && item.centroCustoNome) {
              colabCCMap.set(item.colaboradorNome, item.centroCustoNome);
            }
          });
          matriz = matriz.filter((row: any) => colabCCMap.get(row.colaboradorNome) === this.relatorioCentroCusto);
        }

        this.relatorioDetalhesMatrizOriginal = matriz;
        this.relatorioDetalhesCategoriasColunas = dados.detalhesCategoriasColunas || [];
        
        // Recalcular totais se houver filtro local de centro de custo
        if (this.relatorioCentroCusto) {
          const totais: { [cat: string]: number } = {};
          let totalGeral = 0;
          this.relatorioDetalhesCategoriasColunas.forEach(cat => {
            totais[cat] = 0;
          });
          
          matriz.forEach((row: any) => {
            totalGeral += row.total;
            this.relatorioDetalhesCategoriasColunas.forEach(cat => {
              totais[cat] += (row.valoresPorCategoria[cat] || 0);
            });
          });
          
          this.relatorioDetalhesTotaisPorCategoria = totais;
          this.relatorioDetalhesTotalGeral = totalGeral;
        } else {
          this.relatorioDetalhesTotaisPorCategoria = dados.detalhesTotaisPorCategoria || {};
          this.relatorioDetalhesTotalGeral = dados.detalhesTotalGeral || 0;
        }

        this.filtrarRelatorioDetalhesMatriz();
      },
      error: (err) => {
        console.error("Erro ao carregar dados do relatório", err);
        this.isRelatorioLoading = false;
      }
    });
  }


  exportRelatorioToExcel() {
    if (!this.relatorioDetalhesMatrizFiltrada || this.relatorioDetalhesMatrizFiltrada.length === 0) {
      alert('Não há dados para exportar.');
      return;
    }

    const header = [
      'COLABORADOR',
      'EMPRESA',
      'CENTRO DE CUSTO',
      ...this.relatorioDetalhesCategoriasColunas,
      'TOTAL'
    ];

    const dataRows = this.relatorioDetalhesMatrizFiltrada.map(row => {
      const r = [
        row.colaboradorNome || '-',
        row.empresaNome || '-',
        row.centroCustoCodigo || '-'
      ];
      this.relatorioDetalhesCategoriasColunas.forEach(cat => {
        r.push(row.valoresPorCategoria[cat] || 0);
      });
      r.push(row.total || 0);
      return r;
    });

    const footerRow: any[] = [
      'TOTAL GERAL',
      '',
      ''
    ];
    this.relatorioDetalhesCategoriasColunas.forEach(cat => {
      footerRow.push(this.relatorioDetalhesTotaisPorCategoria[cat] || 0);
    });
    footerRow.push(this.relatorioDetalhesTotalGeral || 0);

    const worksheet: XLSX.WorkSheet = XLSX.utils.aoa_to_sheet([header, ...dataRows, footerRow]);

    worksheet['!views'] = [{
      state: 'frozen',
      xSplit: 1,
      ySplit: 1
    }];

    const workbook: XLSX.WorkBook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Relatório Despesas');
    
    XLSX.writeFile(workbook, 'relatorio-despesas-viagens.xlsx');
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

    this.importacoesService.obterDadosDashboard(filtros).subscribe({
      next: (res) => {
        this.categoryVisaoGeral = {
          total: res.dashVisaoGeral.total,
          quantidadeDespesas: res.dashVisaoGeral.quantidadeDespesas,
          ticketMedio: res.dashVisaoGeral.ticketMedio,
          maiorDespesa: res.dashVisaoGeral.maiorDespesa,
          maiorDespesaContexto: res.dashVisaoGeral.maiorDespesaContexto
        };
        this.categoryTabelaDespesas = res.tabelaMaioresDespesas;
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

