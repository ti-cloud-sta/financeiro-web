import { Component, signal, ViewChild, ElementRef, inject, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

import { NgxEchartsDirective } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import { FlatpickrModule } from 'angularx-flatpickr';
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';

import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { CardComponent } from '../../shared/components/card/card.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { ImportacoesService, Importacao } from '../../core/services/importacoes.service';
import { ColaboradoresService } from '../../core/services/colaboradores.service';
import { CentrosCustoService } from '../../core/services/centros-custo.service';
import { UnidadesService } from '../../core/services/unidades.service';
import { EmpresasService, Empresa } from '../../core/services/empresas.service';
import { PlanoSaudeService, RelatorioGeralRow, ConciliacaoResponse } from '../../core/services/plano-saude.service';
import { ColaboradorModalComponent } from '../../shared/components/colaborador-modal/colaborador-modal.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

export interface HealthPlanCard {
  id: string;
  name: string;
  icon: string;
  colorClass: string;
  status: 'active' | 'upcoming';
  statusText: string;
  statusVariant: 'success' | 'warning' | 'info' | 'primary' | 'secondary';
  description: string;
}

@Component({
  selector: 'app-plano-saude',
  standalone: true,
  imports: [
    CommonModule,
    NgxEchartsDirective,
    FlatpickrModule,
    SkeletonComponent,
    RouterModule,
    FormsModule,
    NgSelectModule,
    CardComponent,
    ButtonComponent,
    ModalComponent,
    LoadingComponent,
    BadgeComponent,
    ColaboradorModalComponent,
    EmptyStateComponent,
    ConfirmModalComponent
  ],
  templateUrl: './plano-saude.component.html',
  styleUrl: './plano-saude.component.scss'
})
export class PlanoSaudeComponent implements OnInit {

  // Gerenciar Empresas Config
  empresasService = inject(EmpresasService);
  activeConfigTab = signal<'empresas'>('empresas');
  listaEmpresasConfig: Empresa[] = [];
  totalEmpresasConfig = 0;
  totalEmpresaConfigPages = 1;
  currentEmpresaConfigPage = 1;
  itemsEmpresaConfigPerPage = 10;
  searchEmpresaConfig = '';

  isEmpresaModalOpen = false;
  empresaModalMode: 'create' | 'edit' = 'create';
  novaEmpresa: Empresa = { nome: '', descricao: '' };
  isSalvandoEmpresa = false;

  setActiveConfigTab(tab: 'empresas') {
    this.activeConfigTab.set(tab);
    if (tab === 'empresas') {
      this.carregarEmpresasConfig();
    }
  }

  carregarEmpresasConfig() {
    this.empresasService.listar(this.currentEmpresaConfigPage, this.itemsEmpresaConfigPerPage, this.searchEmpresaConfig, 2).subscribe({
      next: (res) => {
        this.listaEmpresasConfig = res.items;
        this.totalEmpresasConfig = res.total;
        this.totalEmpresaConfigPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar empresas', err)
    });
  }

  onSearchEmpresaConfigChange(term: string) {
    this.searchEmpresaConfig = term;
    this.currentEmpresaConfigPage = 1;
    this.carregarEmpresasConfig();
  }

  goToEmpresaConfigPage(page: number) {
    if (page >= 1 && page <= this.totalEmpresaConfigPages) {
      this.currentEmpresaConfigPage = page;
      this.carregarEmpresasConfig();
    }
  }

  openEmpresaModal(empresa?: Empresa) {
    if (empresa) {
      this.empresaModalMode = 'edit';
      this.novaEmpresa = { ...empresa };
    } else {
      this.empresaModalMode = 'create';
      this.novaEmpresa = { nome: '', descricao: '' };
    }
    this.isEmpresaModalOpen = true;
  }

  closeEmpresaModal() {
    this.isEmpresaModalOpen = false;
    this.novaEmpresa = { nome: '', descricao: '' };
  }

  salvarEmpresa() {
    if (!this.novaEmpresa.nome) return;
    this.isSalvandoEmpresa = true;
    
    // Always assign modulo_id = 2 when creating from this module
    if (this.empresaModalMode === 'create') {
      this.novaEmpresa.modulo_id = 2;
    }

    if (this.empresaModalMode === 'create') {
      this.empresasService.criar(this.novaEmpresa).subscribe({
        next: () => {
          this.isSalvandoEmpresa = false;
          this.closeEmpresaModal();
          this.carregarEmpresasConfig();
          this.carregarEmpresasAtualizacao(); // also reload cards
        },
        error: (err) => {
          this.isSalvandoEmpresa = false;
          console.error(err);
        }
      });
    } else if (this.novaEmpresa.idEmpresas) {
      this.empresasService.atualizar(this.novaEmpresa.idEmpresas, this.novaEmpresa).subscribe({
        next: () => {
          this.isSalvandoEmpresa = false;
          this.closeEmpresaModal();
          this.carregarEmpresasConfig();
          this.carregarEmpresasAtualizacao();
        },
        error: (err) => {
          this.isSalvandoEmpresa = false;
          console.error(err);
        }
      });
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

  confirmarExclusaoEmpresa(id: number) {
    this.openConfirmModal(
      'Confirmar Exclusão',
      'Tem certeza que deseja excluir esta empresa? Isso apagará permanentemente todos os dados associados a ela.',
      () => {
        this.empresasService.excluir(id).subscribe({
          next: () => {
            this.closeConfirmModal();
            this.carregarEmpresasConfig();
            this.carregarEmpresasAtualizacao();
          },
          error: (err) => {
            this.closeConfirmModal();
            console.error(err);
          }
        });
      }
    );
  }


  // Histórico de Importações
  listaImportacoes: Importacao[] = [];
  totalImportacoes = 0;
  totalImportacaoPages = 0;
  currentImportacaoPage = 1;
  itemsImportacaoPerPage = 10;
  searchImportacaoTerm = '';

  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') !== null
    ? localStorage.getItem('sidebarCollapsed') === 'true'
    : true;
  sidebarTab = signal<'dashboard' | 'atualizacao' | 'relatorios'>('dashboard');
  horizontalTab = signal<'plano-saude' | 'seguro-vida'>('plano-saude');

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  setSidebarTab(tab: 'dashboard' | 'atualizacao' | 'relatorios') {
    this.sidebarTab.set(tab);
  }

  setHorizontalTab(tab: 'plano-saude' | 'seguro-vida') {
    this.horizontalTab.set(tab);
    
    // Reset importation history pagination and reload list
    this.currentImportacaoPage = 1;
    this.carregarImportacoes();

    // Automatically select the first company in the newly selected tab
    const filtered = this.empresasAtualizacao.filter(e => {
      const hasSeguro = e.nome.toLowerCase().includes('seguro');
      return tab === 'seguro-vida' ? hasSeguro : !hasSeguro;
    });
    if (filtered.length > 0) {
      const first = filtered[0];
      this.activeCard.set({
        id: first.idEmpresas!.toString(),
        name: first.nome,
        icon: first.icon || 'fa-solid fa-building',
        colorClass: 'color-info',
        status: 'active',
        statusText: 'Importação Disponível',
        statusVariant: 'success',
        description: first.descricao || ''
      });
    } else {
      this.activeCard.set(null);
    }
  }

  importacoesService = inject(ImportacoesService);
  colaboradoresService = inject(ColaboradoresService);
  centrosCustoService = inject(CentrosCustoService);
  unidadesService = inject(UnidadesService);
  planoSaudeService = inject(PlanoSaudeService);

  colaboradoresList = signal<any[]>([]);
  centrosCustoList = signal<any[]>([]);
  unidadesList = signal<any[]>([]);

  // States for Sorriso health plan import
  parsedTitulares = signal<any[]>([]);
  searchBeneficiaryTerm = signal<string>('');

  filteredParsedTitulares = computed(() => {
    const term = this.searchBeneficiaryTerm().trim().toLowerCase();
    const list = this.parsedTitulares();
    if (!term) return list;
    return list.filter(t => {
      const name = (t.nome_db || t.nome_pdf || '').toLowerCase();
      return name.includes(term);
    });
  });

  // ==========================================
  // RELATÓRIOS (Mock Data)
  // ==========================================
  searchRelatorioTerm = signal<string>('');
  currentRelatorioPage = signal<number>(1);
  itemsRelatorioPerPage = 10;
  totalRelatorioItems = signal<number>(0);
  
  relatorioMes = signal<number>(new Date().getMonth() + 1);
  relatorioAno = signal<number>(new Date().getFullYear());
  relatorioEmpresa = signal<number | null>(null);
  
  isRelatorioLoading = signal<boolean>(false);
  relatoriosData = signal<RelatorioGeralRow[]>([]);
  totalGeralRelatorio = signal<number>(0);

  private searchSubject = new Subject<string>();

  meses = [
    { value: 1, label: 'Janeiro' },
    { value: 2, label: 'Fevereiro' },
    { value: 3, label: 'Março' },
    { value: 4, label: 'Abril' },
    { value: 5, label: 'Maio' },
    { value: 6, label: 'Junho' },
    { value: 7, label: 'Julho' },
    { value: 8, label: 'Agosto' },
    { value: 9, label: 'Setembro' },
    { value: 10, label: 'Outubro' },
    { value: 11, label: 'Novembro' },
    { value: 12, label: 'Dezembro' }
  ];

  anos = computed(() => {
    const currentYear = new Date().getFullYear();
    return [currentYear - 2, currentYear - 1, currentYear, currentYear + 1];
  });

  carregarRelatoriosGerais() {
    this.isRelatorioLoading.set(true);
    this.planoSaudeService.getRelatorioGeral(
      this.relatorioMes(),
      this.relatorioAno(),
      this.searchRelatorioTerm(),
      this.relatorioEmpresa() ? Number(this.relatorioEmpresa()) : undefined,
      this.currentRelatorioPage(),
      this.itemsRelatorioPerPage
    ).subscribe({
      next: (res) => {
        this.relatoriosData.set(res.items);
        this.totalRelatorioItems.set(res.total);
        this.totalGeralRelatorio.set(res.total_valor || 0);
        this.isRelatorioLoading.set(false);
      },
      error: (err) => {
        console.error(err);
        this.isRelatorioLoading.set(false);
      }
    });
  }

  exportarRelatorio() {
    this.isRelatorioLoading.set(true);
    this.planoSaudeService.exportarRelatorioGeral(
      this.relatorioMes(),
      this.relatorioAno(),
      this.searchRelatorioTerm(),
      this.relatorioEmpresa() ? Number(this.relatorioEmpresa()) : undefined
    ).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio_geral_planosaude_${this.relatorioMes().toString().padStart(2, '0')}_${this.relatorioAno()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        this.isRelatorioLoading.set(false);
      },
      error: (err) => {
        console.error('Erro ao exportar relatório', err);
        this.isRelatorioLoading.set(false);
      }
    });
  }

  onRelatorioPeriodoChange() {
    this.currentRelatorioPage.set(1);
    this.carregarRelatoriosGerais();
  }

  totalRelatorioPages = computed(() => {
    return Math.ceil(this.totalRelatorioItems() / this.itemsRelatorioPerPage) || 1;
  });

  goToRelatorioPage(page: number) {
    if (page >= 1 && page <= this.totalRelatorioPages()) {
      this.currentRelatorioPage.set(page);
      this.carregarRelatoriosGerais();
    }
  }

  onSearchRelatorioTermChange(term: string) {
    this.searchSubject.next(term);
  }

  totalGeral = signal<number>(0);
  validacoes = signal<any>(null);
  validacoesSucesso = signal<boolean>(true);
  isSaving = signal<boolean>(false);

  // Colaborador modal integration
  isColaboradorModalOpen = false;
  
  // Conciliação Modal Integration
  isConciliacaoModalOpen = false;
  conciliacaoStep = signal<1 | 2 | 3>(1); // 1 = Upload, 2 = Loading, 3 = Resultado
  conciliacaoResult = signal<ConciliacaoResponse | null>(null);
  conciliacaoFile = signal<File | null>(null);

  colaboradorToCreateName = '';
  editingColaboradorRowId = signal<number | null>(null);

  openCreateColaboradorModal(id: number, titular: any) {
    this.editingColaboradorRowId.set(id);
    this.colaboradorToCreateName = titular.nome_db || titular.nome_pdf || titular.nome;
    this.isColaboradorModalOpen = true;
  }

  onColaboradorSaved(novoColaborador: any) {
    const id = this.editingColaboradorRowId();
    if (id !== null) {
      const currentList = this.parsedTitulares();
      const updatedList = currentList.map(t => {
        if (t._id === id) {
          return {
            ...t,
            id_db: novoColaborador.idColaborador,
            nome_db: novoColaborador.nome,
            centro_custo: 'Mapeado Manualmente'
          };
        }
        return t;
      });
      
      this.carregarColaboradores();
      this.parsedTitulares.set(updatedList);
      
      const allFound = updatedList.every(t => t.centro_custo !== 'N/D');
      this.validacoesSucesso.set(allFound);
    }
    this.isColaboradorModalOpen = false;
    this.editingColaboradorRowId.set(null);
  }

  abrirModalConciliacao() {
    this.conciliacaoStep.set(1);
    this.conciliacaoResult.set(null);
    this.conciliacaoFile.set(null);
    this.isConciliacaoModalOpen = true;
  }

  fecharModalConciliacao() {
    this.isConciliacaoModalOpen = false;
  }

  onConciliacaoFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.processarArquivoConciliacao(file);
    }
  }

  onConciliacaoFileDropped(event: any) {
    event.preventDefault();
    const file = event.dataTransfer?.files[0];
    if (file) {
      this.processarArquivoConciliacao(file);
    }
  }

  onConciliacaoDragOver(event: any) {
    event.preventDefault();
  }

  private processarArquivoConciliacao(file: File) {
    this.conciliacaoFile.set(file);
    this.conciliacaoStep.set(2); // Loading

    this.planoSaudeService.conciliarPlanilha(file).subscribe({
      next: (res) => {
        this.conciliacaoResult.set(res);
        this.conciliacaoStep.set(3); // Result
      },
      error: (err) => {
        console.error('Erro ao processar conciliação', err);
        // Fallback to step 1 on error
        this.conciliacaoStep.set(1);
      }
    });
  }

  // States for inline editing
  editingRowId = signal<number | null>(null);
  editNome = signal<string>('');
  editCentroCusto = signal<string>('');
  editUnidade = signal<string>('');
  editValor = signal<number>(0);

  setParsedTitulares(dados: any[]) {
    const mapped = (dados || []).map((t, idx) => ({ ...t, _id: idx }));
    mapped.sort((a, b) => {
      const nameA = (a.nome_db || a.nome_pdf || '').toLowerCase();
      const nameB = (b.nome_db || b.nome_pdf || '').toLowerCase();
      return nameA.localeCompare(nameB);
    });
    this.parsedTitulares.set(mapped);
  }


  // Dashboard properties
  isDashboardLoading = true;
  locale = Portuguese;
  
  dashDataInicio: Date | null = null;
  dashDataFim: Date | null = null;
  activePeriodShortcut = 'este-ano';
  dashFiltroPessoa: number | null = null;
  dashFiltroCategoria: string = 'TODOS';
  
  chartOptionsEvolucao: any;
  chartOptionsCategorias: any;
  
  topDespesas: any[] = [];
  
  listaColaboradoresGeral: any[] = [];
  
  carregarColaboradoresParaFiltro() {
    this.importacoesService.obterDadosDashboard({}).subscribe({
      next: (res) => {
        this.listaColaboradoresGeral = res.pessoas || [];
      }
    });
  }
  
  isPeriodoValido(): boolean {
    if (this.dashDataInicio && this.dashDataFim) {
      if (this.dashDataInicio > this.dashDataFim) return false;
    }
    return true;
  }

  onDataInicioChange() {
    this.activePeriodShortcut = 'personalizado';
    if (this.isPeriodoValido()) this.carregarDadosDashboard();
  }

  onDataFimChange() {
    this.activePeriodShortcut = 'personalizado';
    if (this.isPeriodoValido()) this.carregarDadosDashboard();
  }
  
  onShortcutSelectChange(shortcut: string) {
    if (shortcut === 'personalizado') return;

    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);

    if (shortcut === 'ultimo-bimestre') {
      const inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 2, 1);
      const fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
      this.dashDataInicio = inicio;
      this.dashDataFim = fim;
    } else if (shortcut === 'ultimo-semestre') {
      const inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 6, 1);
      const fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
      this.dashDataInicio = inicio;
      this.dashDataFim = fim;
    } else if (shortcut === 'este-ano') {
      const inicio = new Date(hoje.getFullYear(), 0, 1);
      this.dashDataInicio = inicio;
      this.dashDataFim = hoje;
    } else if (shortcut === 'ano-passado') {
      const inicio = new Date(hoje.getFullYear() - 1, 0, 1);
      const fim = new Date(hoje.getFullYear() - 1, 11, 31);
      this.dashDataInicio = inicio;
      this.dashDataFim = fim;
    }

    this.activePeriodShortcut = shortcut;
    this.carregarDadosDashboard();
  }

  carregarDadosDashboard() {
    this.isDashboardLoading = true;
    
    const filtros: any = {};
    if (this.dashDataInicio) {
      const offset = this.dashDataInicio.getTimezoneOffset();
      const localDate = new Date(this.dashDataInicio.getTime() - (offset * 60 * 1000));
      filtros.data_inicio = localDate.toISOString().split('T')[0];
    }
    if (this.dashDataFim) {
      const offset = this.dashDataFim.getTimezoneOffset();
      const localDate = new Date(this.dashDataFim.getTime() - (offset * 60 * 1000));
      filtros.data_fim = localDate.toISOString().split('T')[0];
    }
    if (this.dashFiltroPessoa) {
      filtros.id_colaborador = this.dashFiltroPessoa;
    }
    
    if (this.dashFiltroCategoria === 'TODOS') {
      filtros.tipo_importacao = 'PLANO_SAUDE,SEGURO';
    } else {
      filtros.tipo_importacao = this.dashFiltroCategoria;
    }

    this.importacoesService.obterDadosDashboardAnalitico(filtros).subscribe({
      next: (dados) => {
        this.isDashboardLoading = false;
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ec4899', '#06b6d4', '#8b5cf6', '#f43f5e'];

        this.chartOptionsEvolucao = {
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              const val = params[0].value;
              return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
            }
          },
          grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
          xAxis: {
            type: 'category',
            data: dados.meses,
            axisTick: { alignWithLabel: true }
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: (value: number) => {
                return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
              }
            }
          },
          series: [
            {
              name: 'Gasto Mensal',
              type: 'bar',
              barWidth: '45%',
              data: dados.barrasVerticais,
              itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] }
            }
          ]
        };

        this.chartOptionsCategorias = {
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
              const val = params.value;
              return `${params.name}: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)}`;
            }
          },
          legend: { top: 'bottom' },
          series: [
            {
              name: 'Proporção por Tipo',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 5,
                borderColor: '#fff',
                borderWidth: 2
              },
              label: { show: false, position: 'center' },
              emphasis: {
                label: { show: true, fontSize: 16, fontWeight: 'bold' }
              },
              labelLine: { show: false },
              data: (dados.categoriaBarras || []).map((c: any, index: number) => ({
                value: c.value,
                name: c.name,
                itemStyle: { color: colors[index % colors.length] }
              }))
            }
          ]
        };
        this.topDespesas = dados.rankingEmpresas || [];
      },
      error: (err) => {
        console.error('Erro ao carregar dados do dashboard analitico', err);
        this.isDashboardLoading = false;
      }
    });
  }

  ngOnInit() {
    this.carregarRelatoriosGerais();
    this.searchSubject.pipe(
      debounceTime(400),
      distinctUntilChanged()
    ).subscribe(term => {
      this.searchRelatorioTerm.set(term);
      this.currentRelatorioPage.set(1);
      this.carregarRelatoriosGerais();
    });

    this.carregarColaboradoresParaFiltro();
    this.onShortcutSelectChange('este-ano');

    this.carregarEmpresasAtualizacao();
    this.carregarEmpresasConfig();
    this.carregarColaboradores();
    this.carregarCentrosCusto();
    this.carregarUnidades();
    this.carregarImportacoes();
  }

  carregarColaboradores() {
    this.colaboradoresService.listar(1, 2000).subscribe({
      next: (res) => {
        const list = res.items || [];
        this.colaboradoresList.set(list.sort((a, b) => a.nome.localeCompare(b.nome)));
      }
    });
  }

  carregarCentrosCusto() {
    this.centrosCustoService.listar(1, 200).subscribe({
      next: (res) => {
        const list = res.items || [];
        this.centrosCustoList.set(list.sort((a, b) => a.codigo - b.codigo));
      }
    });
  }

  carregarUnidades() {
    this.unidadesService.listar(1, 200).subscribe({
      next: (res) => {
        const list = res.items || [];
        this.unidadesList.set(list.sort((a, b) => a.descricao.localeCompare(b.descricao)));
      }
    });
  }

  cards = signal<HealthPlanCard[]>([
    {
      id: 'unimed-norte-paulista',
      name: 'Unimed Norte Paulista',
      icon: 'fa-solid fa-notes-medical',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação de faturas e composição de custos Unimed Norte Paulista.'
    },
    {
      id: 'seguro-vida',
      name: 'Seguro de Vida',
      icon: 'fa-solid fa-hand-holding-heart',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação de apólices e controle de movimentação de Seguro de Vida.'
    },
    {
      id: 'seguro-saude',
      name: 'Seguro Saude',
      icon: 'fa-solid fa-heart-pulse',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação e conciliação de faturas de Seguro Saúde corporativo.'
    },
    {
      id: 'seguro-unimed',
      name: 'Seguro Unimed',
      icon: 'fa-solid fa-shield-halved',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação e cruzamento de guias e faturas do Seguro Unimed.'
    },
    {
      id: 'sorriso',
      name: 'Sorriso',
      icon: 'fa-solid fa-tooth',
      colorClass: 'text-info bg-info-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação de faturas e planos odontológicos Sorriso.'
    },
    {
      id: 'unimed-odonto',
      name: 'Unimed Odonto',
      icon: 'fa-solid fa-smile-beam',
      colorClass: 'text-info bg-info-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação de demonstrativos e faturas odontológicas Unimed Odonto.'
    },
    {
      id: 'capixaba',
      name: 'Capixaba',
      icon: 'fa-solid fa-hospital',
      colorClass: 'text-warning bg-warning-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success',
      description: 'Importação de guias e demonstrativos de custos Capixaba Saúde.'
    }
  ]);

  activeCards = computed(() => {
    if (this.horizontalTab() === 'plano-saude') {
      return this.cards().filter(c => c.id !== 'seguro-vida');
    }
    return this.cards().filter(c => c.id === 'seguro-vida');
  });

  activeCard = signal<HealthPlanCard | null>(null);
  selectedFile = signal<File | null>(null);
  isUploadModalOpen = signal<boolean>(false);
  isProcessing = signal<boolean>(false);
  processingStep = signal<number>(0);
  processingText = signal<string>('');
  processingError = signal<string>('');
  importedCount = signal<number>(0);
  divergencesCount = signal<number>(0);

  triggerImport(card: HealthPlanCard) {
    this.activeCard.set(card);
    this.selectedFile.set(null);
    this.processingError.set('');
    this.processingStep.set(0);
    this.isProcessing.set(false);
    
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
      this.fileInput.nativeElement.click();
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile.set(input.files[0]);
      this.isUploadModalOpen.set(true);
    }
  }

  processFile() {
    if (!this.selectedFile() || !this.activeCard()) return;

    this.processingError.set('');
    this.isProcessing.set(true);
    this.processingStep.set(1);
    this.processingText.set('Extraindo dados do arquivo...');

    this.importacoesService.analisarUniversal(this.selectedFile()!).subscribe({
      next: (res) => {
        if (res.sucesso) {
          this.setParsedTitulares(res.dados);
          this.totalGeral.set(res.total_geral);
          this.validacoes.set(res.validacoes);
          this.validacoesSucesso.set(res.validacoes_sucesso);
          this.processingStep.set(5);
          this.isProcessing.set(false);
        } else {
          this.processingError.set('Erro ao analisar arquivo.');
          this.isProcessing.set(false);
        }
      },
      error: (err) => {
        this.processingError.set(err.error?.detail || 'Erro ao comunicar com o servidor.');
        this.isProcessing.set(false);
      }
    });
  }

  confirmAndSave() {
    if (!this.selectedFile() || this.parsedTitulares().length === 0) return;

    this.isSaving.set(true);
    this.processingError.set('');

    const activeId = this.activeCard()?.id;
    const cardNameLower = this.activeCard()?.name?.toLowerCase() || '';
    const isSeguroTab = this.horizontalTab() === 'seguro-vida';
    const idEmpresa = (activeId !== 'unimed-odonto' && activeId !== 'sorriso') ? parseInt(activeId || '0') : undefined;

    // Determine whether to use Unimed Odonto schema/endpoint or Sorriso schema/endpoint
    const useUnimedOdontoSchema = !isSeguroTab && (activeId === 'unimed-odonto' || cardNameLower.includes('unimed') || cardNameLower.includes('odonto'));

    if (useUnimedOdontoSchema) {
      this.importacoesService.confirmarUnimedOdonto(this.selectedFile()!.name, this.parsedTitulares(), idEmpresa).subscribe({
        next: (res) => {
          this.isSaving.set(false);
          if (res.sucesso) {
            this.importedCount.set(res.movimentacoes_criadas);
            this.divergencesCount.set(res.erros_colaboradores ? res.erros_colaboradores.length : 0);
            this.processingStep.set(4);
            this.carregarImportacoes();
          } else {
            this.processingError.set('Erro ao salvar os dados.');
          }
        },
        error: (err) => {
          this.isSaving.set(false);
          this.processingError.set(err.error?.detail || 'Erro ao salvar os dados no banco.');
        }
      });
    } else {
      // Use Sorriso schema/endpoint (standard for Gemini dynamic extractions, including Seguros)
      this.importacoesService.confirmarSorriso(this.selectedFile()!.name, this.parsedTitulares(), idEmpresa).subscribe({
        next: (res) => {
          this.isSaving.set(false);
          if (res.sucesso) {
            this.importedCount.set(res.movimentacoes_criadas);
            this.divergencesCount.set(res.erros_colaboradores ? res.erros_colaboradores.length : 0);
            this.processingStep.set(4);
            this.carregarImportacoes();
          } else {
            this.processingError.set('Erro ao salvar os dados.');
          }
        },
        error: (err) => {
          this.isSaving.set(false);
          this.processingError.set(err.error?.detail || 'Erro ao salvar os dados no banco.');
        }
      });
    }
  }

  closeModal() {
    this.isUploadModalOpen.set(false);
    this.activeCard.set(null);
    this.selectedFile.set(null);
    this.processingStep.set(0);
    this.editingRowId.set(null);
    this.isAddingBeneficiario.set(false);
    if (this.isPeriodoValido()) {
      this.carregarDadosDashboard();
    }
  }

  onColaboradorSelected(colabNome: string) {
    const colab = this.colaboradoresList().find(c => c.nome === colabNome);
    if (colab) {
      if (colab.centro_custo) {
        this.editCentroCusto.set(colab.centro_custo.codigo.toString());
      }
      if (colab.unidades && colab.unidades.length) {
        this.editUnidade.set(colab.unidades.map((u: any) => u.codigo).join(', '));
      }
    }
  }

  // Inline editing methods
  onEditNomeChange(event: Event) {
    const val = (event.target as HTMLInputElement).value;
    this.editNome.set(val);
  }

  onEditCCChange(event: Event) {
    const val = (event.target as HTMLInputElement).value;
    this.editCentroCusto.set(val);
  }

  onEditUnidadeChange(event: Event) {
    const val = (event.target as HTMLInputElement).value;
    this.editUnidade.set(val);
  }

  onEditValorChange(event: Event) {
    const val = parseFloat((event.target as HTMLInputElement).value) || 0;
    this.editValor.set(val);
  }

  startEdit(id: number, titular: any) {
    this.editingRowId.set(id);
    this.editNome.set(titular.nome_db || titular.nome_pdf);
    this.editCentroCusto.set(titular.centro_custo || 'N/D');
    this.editUnidade.set(titular.unidade || 'N/D');
    this.editValor.set(titular.valor_total);
  }

  saveEdit(id: number) {
    const updatedList = [...this.parsedTitulares()];
    const index = updatedList.findIndex(t => t._id === id);
    if (index >= 0) {
      const item = { ...updatedList[index] };
      item.nome_db = this.editNome();
      item.centro_custo = this.editCentroCusto()?.toString() || 'N/D';
      item.unidade = this.editUnidade() || 'N/D';
      item.valor_total = this.editValor();
      updatedList[index] = item;
      
      // Re-sort alphabetically since the name might have changed!
      updatedList.sort((a, b) => {
        const nameA = (a.nome_db || a.nome_pdf || '').toLowerCase();
        const nameB = (b.nome_db || b.nome_pdf || '').toLowerCase();
        return nameA.localeCompare(nameB);
      });
      
      this.parsedTitulares.set(updatedList);
      this.editingRowId.set(null);
      this.recalculateTotalGeral();
    }
  }

  cancelEdit() {
    this.editingRowId.set(null);
  }

  recalculateTotalGeral() {
    const sum = this.parsedTitulares().reduce((acc, curr) => acc + (curr.valor_total || 0), 0);
    this.totalGeral.set(sum);
  }

  // Adicionar beneficiário manualmente (colaborador já cadastrado + valor)
  isAddingBeneficiario = signal<boolean>(false);
  newBeneficiarioNome = signal<string>('');
  newBeneficiarioValor = signal<number>(0);

  startAddBeneficiario() {
    this.newBeneficiarioNome.set('');
    this.newBeneficiarioValor.set(0);
    this.isAddingBeneficiario.set(true);
  }

  cancelAddBeneficiario() {
    this.isAddingBeneficiario.set(false);
  }

  onNewBeneficiarioValorChange(event: Event) {
    const val = parseFloat((event.target as HTMLInputElement).value) || 0;
    this.newBeneficiarioValor.set(val);
  }

  confirmAddBeneficiario() {
    const nome = this.newBeneficiarioNome();
    if (!nome) return;

    const colab = this.colaboradoresList().find(c => c.nome === nome);
    const centroCusto = colab?.centro_custo ? colab.centro_custo.codigo.toString() : 'N/D';
    const unidade = colab?.unidade ? colab.unidade.codigo.toString() : 'N/D';
    const valor = this.newBeneficiarioValor();

    const currentList = this.parsedTitulares();
    const maxId = currentList.reduce((max, t) => Math.max(max, t._id), -1);

    const novoItem = {
      _id: maxId + 1,
      nome_pdf: nome,
      nome_db: nome,
      valor_titular: valor,
      dependentes: [],
      valor_total: valor,
      centro_custo: centroCusto,
      unidade: unidade
    };

    const updatedList = [...currentList, novoItem];
    updatedList.sort((a, b) => {
      const nameA = (a.nome_db || a.nome_pdf || '').toLowerCase();
      const nameB = (b.nome_db || b.nome_pdf || '').toLowerCase();
      return nameA.localeCompare(nameB);
    });

    this.parsedTitulares.set(updatedList);
    this.recalculateTotalGeral();
    this.isAddingBeneficiario.set(false);
  }

  exportToExcel() {
    if (this.parsedTitulares().length === 0) return;

    if (this.activeCard()?.id === 'sorriso') {
      this.importacoesService.exportarSorrisoExcel(this.parsedTitulares()).subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'planilha_consolidada_sorriso.xlsx';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        },
        error: (err) => {
          this.processingError.set('Erro ao exportar planilha Excel.');
        }
      });
    } else if (this.activeCard()?.id === 'unimed-odonto') {
      this.importacoesService.exportarUnimedOdontoExcel(this.parsedTitulares()).subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'planilha_consolidada_unimed_odonto.xlsx';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        },
        error: (err) => {
          this.processingError.set('Erro ao exportar planilha Excel.');
        }
      });
    }
  }

  carregarImportacoes() {
    const categoria = this.horizontalTab() === 'seguro-vida' ? 'SEGURO' : 'PLANO_SAUDE';
    this.importacoesService.listar(this.currentImportacaoPage, this.itemsImportacaoPerPage, this.searchImportacaoTerm, categoria).subscribe({
      next: (res) => {
        this.listaImportacoes = res.items;
        this.totalImportacoes = res.total;
        this.totalImportacaoPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar importacoes', err)
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

  confirmarExclusaoImportacao(id: number) {
    this.openConfirmModal(
      'Confirmar Exclusão',
      'Tem certeza que deseja excluir esta importação? Esta ação removerá permanentemente o registro de histórico e todas as suas movimentações financeiras associadas.',
      () => {
        this.importacoesService.excluir(id).subscribe({
          next: () => {
            this.closeConfirmModal();
            this.carregarImportacoes();
          },
          error: (err) => {
            this.closeConfirmModal();
            console.error(err);
          }
        });
      }
    );
  }


  isDuplicated(nome: string): boolean {
    if (!nome) return false;
    const nameLower = nome.trim().toLowerCase();
    const count = this.parsedTitulares().filter(t => {
      const tName = (t.nome_db || t.nome_pdf || '').trim().toLowerCase();
      return tName === nameLower;
    }).length;
    return count > 1;
  }

  // Empresas for Atualizacao cards
  empresasAtualizacao: Empresa[] = [];

  get filteredEmpresasAtualizacao(): Empresa[] {
    const tab = this.horizontalTab();
    return this.empresasAtualizacao.filter(e => {
      const hasSeguro = e.nome.toLowerCase().includes('seguro');
      if (tab === 'seguro-vida') {
        return hasSeguro;
      } else {
        return !hasSeguro;
      }
    });
  }

  carregarEmpresasAtualizacao() {
    // Busca as empresas vinculadas a este módulo (ID = 2)
    this.empresasService.listar(1, 100, '', 2).subscribe({
      next: (res) => {
        this.empresasAtualizacao = res.items.map(e => {
          // Atribui ícones baseados no nome
          const nomeLower = e.nome.toLowerCase();
          if (nomeLower.includes('seguro')) {
            e.icon = 'fa-solid fa-shield-halved';
          } else if (nomeLower.includes('odonto') || nomeLower.includes('sorriso')) {
            e.icon = 'fa-solid fa-tooth';
          } else {
            e.icon = 'fa-solid fa-briefcase-medical';
          }
          return e;
        });
        
        // Define initial active card based on the current tab
        const tab = this.horizontalTab();
        const filtered = this.empresasAtualizacao.filter(e => {
          const hasSeguro = e.nome.toLowerCase().includes('seguro');
          return tab === 'seguro-vida' ? hasSeguro : !hasSeguro;
        });
        
        if (filtered.length > 0 && (!this.activeCard() || !filtered.find(e => e.idEmpresas?.toString() === this.activeCard()?.id))) {
           const first = filtered[0];
           this.activeCard.set({
              id: first.idEmpresas!.toString(),
              name: first.nome,
              icon: first.icon || 'fa-solid fa-building',
              colorClass: 'color-info',
              status: 'active',
              statusText: 'Importação Disponível',
              statusVariant: 'success',
              description: first.descricao || ''
           });
        }
      },
      error: (err) => console.error('Erro ao carregar empresas atualizacao', err)
    });
  }

}