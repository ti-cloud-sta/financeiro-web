import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FlatpickrModule } from 'angularx-flatpickr';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';
import { ImportacoesService, PendenciaKanban, JanelaRegraDia } from '../../../../../core/services/importacoes.service';
import { PendenciaDetalheModalComponent, STATUS_OPTIONS } from './components/pendencia-detalhe-modal/pendencia-detalhe-modal.component';
import { ModalComponent } from '../../../../../shared/components/modal/modal.component';
import { PendenciaLoteModalComponent } from './components/pendencia-lote-modal/pendencia-lote-modal.component';
import { ButtonComponent } from '../../../../../shared/components/button/button.component';

export interface KanbanCard {
  id: string;
  title: string;
  status: string;
  statusColor: string;
  clientName: string;
  fullClientName?: string;
  dtVencimento: Date | null;
  leadTimeDays: number | null;
  isDevolucao: boolean;
  
  // Real details for modal
  fase: string | null;
  idCliente: number | null;
  especie: string | null;
  carteira: string | null;
  idUnidade: number | null;
  serie: string | null;
  parccela: string | null;
  portador: string | null;
  dtEmissao: Date | null;
  dtEntrega: Date | null;
  valorOriginal: number | null;
  valorSaldo: number | null;
}

export interface KanbanColumn {
  id: string;
  title: string;
  icon: string;
  colorClass: string;
  cards: KanbanCard[];
}

type PeriodShortcut = 'vencidas' | 'ult-vencimento' | 'este-mes' | 'este-semestre' | 'este-ano' | 'personalizado';

const COLUMN_VISIBILITY_STORAGE_KEY = 'pendencias_colunas_visiveis';

const CLIENT_NAME_MAX_LENGTH = 28;

function loadVisibleColumnIds(allIds: string[]): Set<string> {
  try {
    const raw = localStorage.getItem(COLUMN_VISIBILITY_STORAGE_KEY);
    if (raw !== null) {
      const saved: string[] = JSON.parse(raw);
      return new Set(saved.filter(id => allIds.includes(id)));
    }
  } catch {
    // localStorage indisponível ou dado corrompido: usa o padrão (todas visíveis)
  }
  return new Set(allIds);
}

function saveVisibleColumnIds(ids: Set<string>) {
  try {
    localStorage.setItem(COLUMN_VISIBILITY_STORAGE_KEY, JSON.stringify(Array.from(ids)));
  } catch {
    // ignora falha ao persistir a preferência
  }
}

@Component({
  selector: 'app-pendencias',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FlatpickrModule,
    PendenciaDetalheModalComponent,
    PendenciaLoteModalComponent,
    ModalComponent,
    ButtonComponent
  ],
  templateUrl: './pendencias.component.html',
  styleUrl: './pendencias.component.scss'
})
export class PendenciasComponent implements OnInit {
  private importacoesService = inject(ImportacoesService);

  locale = Portuguese;

  dataInicio: Date | null = null;
  dataFim: Date | null = null;
  activePeriodShortcut: PeriodShortcut | null = null;
  statusFiltro: string | null = null;
  textoFiltro: string = '';
  filtroDevolucaoAtivo = false;
  filtroProtestadoAtivo = false;
  isLoading = false;

  // Seleção e Disparo em Lote
  selectedCardsMap = new Map<string, KanbanCard>();
  isModalLoteOpen = false;

  // Drop Status Modal state
  isDropStatusModalOpen = false;
  dropStatusSelecionado = '';
  todasOpcoesStatus = STATUS_OPTIONS;
  pendingDropCard: KanbanCard | null = null;
  pendingDropSourceColId: string | null = null;
  pendingDropDestColId: string | null = null;

  // Atalho "Regra do Dia": mesma janela de vencimento (critério de dia da semana) que antes
  // travava a importação - agora é só informativa, calculada pelo backend.
  regraDiaAplicavel = false;
  regraDiaInicio: string | null = null;
  regraDiaFim: string | null = null;
  regraDiaDiaSemana = '';

  columns: KanbanColumn[] = [
    { id: 'pendencias', title: 'Pendências', icon: 'fa-solid fa-triangle-exclamation', colorClass: 'danger', cards: [] },
    { id: 'logistica', title: 'Logística', icon: 'fa-solid fa-truck', colorClass: 'warning', cards: [] },
    { id: 'fiscal', title: 'Fiscal', icon: 'fa-regular fa-file-lines', colorClass: 'info', cards: [] },
    { id: 'comercial', title: 'Comercial', icon: 'fa-solid fa-cart-shopping', colorClass: 'primary', cards: [] },
    { id: 'financeiro', title: 'Financeiro', icon: 'fa-solid fa-dollar-sign', colorClass: 'secondary', cards: [] },
    { id: 'finalizado', title: 'Finalizado', icon: 'fa-solid fa-circle-check', colorClass: 'success', cards: [] },
  ];

  visibleColumnIds: Set<string> = loadVisibleColumnIds(this.columns.map(c => c.id));
  isColumnFilterOpen = false;

  isDetalheModalOpen = false;
  cardSelecionado: KanbanCard | null = null;

  abrirDetalhes(card: KanbanCard) {
    this.cardSelecionado = card;
    this.isDetalheModalOpen = true;
  }

  fecharDetalhes() {
    this.isDetalheModalOpen = false;
  }

  @ViewChild('columnFilterWrapper') columnFilterWrapper?: ElementRef<HTMLElement>;

  ngOnInit() {
    this.limparPeriodo();
    this.carregarJanelaRegraDia();
  }

  carregarPendencias() {
    this.isLoading = true;
    const inicio = this.dataInicio ? this.formatarISO(this.dataInicio) : undefined;
    const fim = this.dataFim ? this.formatarISO(this.dataFim) : undefined;
    this.importacoesService.listarPendenciasInadimplencia(inicio, fim).subscribe({
      next: (itens) => {
        this.isLoading = false;
        this.aplicarPendencias(itens);
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Erro ao carregar pendências:', err);
      }
    });
  }

  carregarJanelaRegraDia() {
    this.importacoesService.obterJanelaRegraDia().subscribe({
      next: (res: JanelaRegraDia) => {
        this.regraDiaAplicavel = res.aplicavel;
        this.regraDiaInicio = res.inicio || null;
        this.regraDiaFim = res.fim || null;
        this.regraDiaDiaSemana = res.diaSemanaHoje;
      },
      error: (err) => console.error('Erro ao obter janela da regra do dia:', err)
    });
  }

  private formatarISO(data: Date): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}`;
  }

  private aplicarPendencias(itens: PendenciaKanban[]) {
    const colunaPorFase = new Map(this.columns.map(col => [col.id, col]));
    this.columns.forEach(col => col.cards = []);

    for (const item of itens) {
      const colunaId = (item.fase || '').toLowerCase();
      const coluna = colunaPorFase.get(colunaId);
      if (!coluna) continue; // fase sem coluna correspondente no board

      coluna.cards.push({
        id: item.idnfpendencias.toString(),
        title: item.titulo || '-',
        status: item.status || '-',
        statusColor: item.status === 'OK' ? 'success' : (item.status === 'PRORROGADO' ? 'info' : (item.status === 'DEVOLUCAO' ? 'orange' : (item.status === 'PROTESTADO' ? 'danger' : (item.status === 'ATRASADO' ? 'warning' : coluna.colorClass)))),
        clientName: this.sliceClientName(item.clienteNome),
        fullClientName: item.clienteNome || '-',
        dtVencimento: item.dtVencimento ? new Date(item.dtVencimento + 'T00:00:00') : null,
        leadTimeDays: this.calcularDiasDesdeImportacao(item.createdAt),
        isDevolucao: item.devolucao === 'S',
        
        fase: item.fase,
        idCliente: item.idCliente,
        especie: item.especie,
        carteira: item.carteira,
        idUnidade: item.idUnidade,
        serie: item.serie,
        parccela: item.parccela,
        portador: item.portador,
        dtEmissao: item.dtEmissao ? new Date(item.dtEmissao + 'T00:00:00') : null,
        dtEntrega: item.dtEntrega ? new Date(item.dtEntrega + 'T00:00:00') : null,
        valorOriginal: item.valorOriginal,
        valorSaldo: item.valorSaldo
      });
    }

    // Sincroniza os cards selecionados com a nova listagem
    const todosCardsNovos = new Map<string, KanbanCard>();
    for (const col of this.columns) {
      for (const card of col.cards) {
        todosCardsNovos.set(card.id, card);
      }
    }
    for (const id of Array.from(this.selectedCardsMap.keys())) {
      const atualizado = todosCardsNovos.get(id);
      if (atualizado) {
        this.selectedCardsMap.set(id, atualizado);
      } else {
        this.selectedCardsMap.delete(id);
      }
    }
  }

  private calcularDiasDesdeImportacao(createdAt: string | null): number | null {
    if (!createdAt) return null;
    const importadoEm = new Date(createdAt);
    const hoje = new Date();
    const msPorDia = 1000 * 60 * 60 * 24;
    const diffDias = Math.floor(
      (Date.UTC(hoje.getFullYear(), hoje.getMonth(), hoje.getDate()) -
        Date.UTC(importadoEm.getFullYear(), importadoEm.getMonth(), importadoEm.getDate())) / msPorDia
    );
    return Math.max(diffDias, 0);
  }

  private sliceClientName(nome: string | null): string {
    if (!nome) return '-';
    return nome.length > CLIENT_NAME_MAX_LENGTH
      ? nome.slice(0, CLIENT_NAME_MAX_LENGTH) + '…'
      : nome;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (!this.isColumnFilterOpen) return;
    const wrapperEl = this.columnFilterWrapper?.nativeElement;
    if (wrapperEl && !wrapperEl.contains(event.target as Node)) {
      this.isColumnFilterOpen = false;
    }
  }

  onStatusFiltroChange(novoStatus: string | null) {
    if (novoStatus === 'DEVOLUCAO') {
      this.filtroDevolucaoAtivo = true;
    }
    if (novoStatus === 'PROTESTADO') {
      this.filtroProtestadoAtivo = true;
    }
  }

  get statusOptions(): string[] {
    return STATUS_OPTIONS;
  }

  get visibleColumnsLabel(): string {
    const total = this.columns.length;
    const visible = this.visibleColumnIds.size;
    if (visible === total) return 'Todas as colunas';
    if (visible === 0) return 'Nenhuma coluna';
    return `${visible} de ${total} colunas`;
  }

  toggleColumnFilterOpen() {
    this.isColumnFilterOpen = !this.isColumnFilterOpen;
  }

  isColumnVisible(columnId: string): boolean {
    return this.visibleColumnIds.has(columnId);
  }

  toggleColumnVisibility(columnId: string) {
    if (this.visibleColumnIds.has(columnId)) {
      this.visibleColumnIds.delete(columnId);
    } else {
      this.visibleColumnIds.add(columnId);
    }
    saveVisibleColumnIds(this.visibleColumnIds);
  }

  get filteredColumns(): KanbanColumn[] {
    return this.columns
      .filter(column => this.visibleColumnIds.has(column.id))
      .map(column => ({
        ...column,
        cards: column.cards.filter(card => {
          if (column.id === 'logistica') {
            const isDevolucao = card.status === 'DEVOLUCAO';
            if (this.filtroDevolucaoAtivo && !isDevolucao) return false;
            if (!this.filtroDevolucaoAtivo && isDevolucao) return false;
          }
          if (column.id === 'financeiro') {
            const isProtestado = card.status === 'PROTESTADO';
            if (this.filtroProtestadoAtivo && !isProtestado) return false;
            if (!this.filtroProtestadoAtivo && isProtestado) return false;
          }
          return this.cardMatchesFilters(card);
        })
      }));
  }

  private cardMatchesFilters(card: KanbanCard): boolean {
    // O filtro de período (data) já é aplicado pelo backend em carregarPendencias()
    if (this.statusFiltro && this.statusFiltro !== 'null' && card.status !== this.statusFiltro) {
      return false;
    }
    
    if (this.textoFiltro && this.textoFiltro.trim() !== '') {
      const term = this.textoFiltro.toLowerCase().trim();
      const searchableFields = [
        card.id,
        card.title,
        card.status,
        card.clientName,
        card.fase,
        card.idCliente,
        card.especie,
        card.carteira,
        card.idUnidade,
        card.serie,
        card.parccela,
        card.portador,
        card.valorOriginal,
        card.valorSaldo
      ];
      const fullText = searchableFields.join(' ').toLowerCase();
      
      if (!fullText.includes(term)) {
        return false;
      }
    }
    
    return true;
  }

  onDataInicioChange() {
    if (this.dataInicio && this.dataFim && this.dataInicio > this.dataFim) {
      this.dataFim = this.dataInicio;
    }
    if (!this.dataInicio && !this.dataFim) {
      this.activePeriodShortcut = 'vencidas';
    } else {
      this.activePeriodShortcut = 'personalizado';
    }
    this.carregarPendencias();
  }

  onDataFimChange() {
    if (!this.dataInicio && !this.dataFim) {
      this.activePeriodShortcut = 'vencidas';
    } else {
      this.activePeriodShortcut = 'personalizado';
    }
    this.carregarPendencias();
  }

  onShortcutSelectChange(val: PeriodShortcut) {
    if (!val || val === 'personalizado') return;
    if (val === 'vencidas') {
      this.limparPeriodo();
      return;
    }
    this.selecionarAtalhoPeriodo(val);
    this.carregarPendencias();
  }

  limparPeriodo() {
    this.dataInicio = null;
    this.dataFim = null;
    this.activePeriodShortcut = 'vencidas';
    this.carregarPendencias();
  }

  selecionarAtalhoPeriodo(shortcut: Exclude<PeriodShortcut, 'personalizado' | 'vencidas'>) {
    const today = new Date();

    if (shortcut === 'ult-vencimento') {
      const diaSemana = today.getDay(); // 0 = Domingo, 1 = Segunda, 2 = Terça, 3 = Quarta, 4 = Quinta, 5 = Sexta, 6 = Sábado
      if (diaSemana === 1) {
        // Segunda-feira: títulos que venceram na sexta-feira anterior (hoje - 3 dias)
        const sexta = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 3);
        this.dataInicio = sexta;
        this.dataFim = new Date(sexta);
      } else if (diaSemana === 2) {
        // Terça-feira: títulos que venceram no sábado, domingo ou segunda (hoje - 3 dias até hoje - 1 dia)
        const sabado = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 3);
        const segunda = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
        this.dataInicio = sabado;
        this.dataFim = segunda;
      } else if (diaSemana === 0) {
        // Domingo: sexta-feira anterior
        const sexta = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 2);
        this.dataInicio = sexta;
        this.dataFim = new Date(sexta);
      } else if (diaSemana === 6) {
        // Sábado: sexta-feira anterior
        const sexta = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
        this.dataInicio = sexta;
        this.dataFim = new Date(sexta);
      } else {
        // Quarta, Quinta, Sexta: exatamente o dia anterior (hoje - 1 dia)
        const ontem = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
        this.dataInicio = ontem;
        this.dataFim = new Date(ontem);
      }
    } else if (shortcut === 'este-mes') {
      this.dataInicio = new Date(today.getFullYear(), today.getMonth(), 1);
      this.dataFim = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    } else if (shortcut === 'este-semestre') {
      const isPrimeiroSemestre = today.getMonth() < 6;
      this.dataInicio = new Date(today.getFullYear(), isPrimeiroSemestre ? 0 : 6, 1);
      this.dataFim = new Date(today.getFullYear(), isPrimeiroSemestre ? 5 : 11, isPrimeiroSemestre ? 30 : 31);
    } else if (shortcut === 'este-ano') {
      this.dataInicio = new Date(today.getFullYear(), 0, 1);
      this.dataFim = new Date(today.getFullYear(), 11, 31);
    }

    this.activePeriodShortcut = shortcut;
  }

  draggedCard: KanbanCard | null = null;
  sourceColumnId: string | null = null;
  dragOverColumnId: string | null = null;

  onDragStart(event: DragEvent, card: KanbanCard, column: KanbanColumn) {
    this.draggedCard = card;
    this.sourceColumnId = column.id;
    
    // Pequeno atraso para permitir que o navegador gere a imagem ghost antes de reduzirmos a opacidade
    setTimeout(() => {
      if (event.target instanceof HTMLElement) {
        event.target.classList.add('dragging');
      }
    }, 0);
  }

  onDragEnd(event: DragEvent) {
    if (event.target instanceof HTMLElement) {
      event.target.classList.remove('dragging');
    }
    this.draggedCard = null;
    this.sourceColumnId = null;
    this.dragOverColumnId = null;
  }

  onDragOver(event: DragEvent) {
    // Essencial para permitir que o drop aconteça nesta zona
    event.preventDefault();
  }
  
  onDragEnter(event: DragEvent, column: KanbanColumn) {
    event.preventDefault();
    if (this.draggedCard && this.sourceColumnId !== column.id) {
      this.dragOverColumnId = column.id;
    }
  }

  onDragLeave(event: DragEvent, column: KanbanColumn) {
    // dragenter/dragleave se comportam como mouseover/mouseout: ao passar por cima
    // de um card interno, o navegador dispara um dragleave da column-body antes do
    // dragenter do card (que borbulha de volta pra column-body). Se o elemento para
    // onde o mouse foi (relatedTarget) ainda está dentro da column-body, ignoramos
    // esse leave para não remover e reaplicar a classe a cada card sobrevoado.
    const columnBody = event.currentTarget as HTMLElement;
    const relatedTarget = event.relatedTarget as Node | null;
    if (relatedTarget && columnBody.contains(relatedTarget)) {
      return;
    }

    if (this.dragOverColumnId === column.id) {
      this.dragOverColumnId = null;
    }
  }

  onDrop(event: DragEvent, targetColumn: KanbanColumn) {
    event.preventDefault();
    this.dragOverColumnId = null;

    if (this.draggedCard && this.sourceColumnId && this.sourceColumnId !== targetColumn.id) {
      const card = this.draggedCard;
      const idColunaOrigem = this.sourceColumnId;
      const idColunaDestino = targetColumn.id;

      if (idColunaOrigem === 'finalizado' && idColunaDestino !== 'finalizado') {
        this.pendingDropCard = card;
        this.pendingDropSourceColId = idColunaOrigem;
        this.pendingDropDestColId = idColunaDestino;
        this.dropStatusSelecionado = '';
        this.isDropStatusModalOpen = true;
        return;
      }

      this.executarDrop(card, idColunaOrigem, idColunaDestino);
    }
  }

  private executarDrop(card: KanbanCard, idColunaOrigem: string, idColunaDestino: string, novoStatus?: string) {
    const sourceCol = this.columns.find(c => c.id === idColunaOrigem);
    if (sourceCol) {
      sourceCol.cards = sourceCol.cards.filter(c => c.id !== card.id);
    }

    const destCol = this.columns.find(c => c.id === idColunaDestino);
    if (destCol) {
      card.statusColor = destCol.colorClass;
      if (idColunaDestino === 'finalizado') {
        card.status = 'OK';
        card.statusColor = 'success';
      } else if (novoStatus) {
        card.status = novoStatus;
      }
      destCol.cards.push(card);
    }

    this.importacoesService.alterarFasePendencia(Number(card.id), idColunaDestino.toUpperCase(), novoStatus).subscribe({
      error: (err) => {
        console.error('Erro ao mover pendência entre colunas:', err);
        if (destCol) {
          destCol.cards = destCol.cards.filter(c => c.id !== card.id);
        }
        if (sourceCol) {
          card.statusColor = sourceCol.colorClass;
          sourceCol.cards.push(card);
        }
      }
    });
  }

  confirmarStatusDrop() {
    if (!this.dropStatusSelecionado) return;
    if (this.pendingDropCard && this.pendingDropSourceColId && this.pendingDropDestColId) {
      this.executarDrop(this.pendingDropCard, this.pendingDropSourceColId, this.pendingDropDestColId, this.dropStatusSelecionado);
    }
    this.fecharStatusDrop();
  }

  fecharStatusDrop() {
    this.isDropStatusModalOpen = false;
    this.pendingDropCard = null;
    this.pendingDropSourceColId = null;
    this.pendingDropDestColId = null;
    this.dropStatusSelecionado = '';
  }

  // ------------------------------------------------------------
  // Métodos de Seleção e Ações em Lote
  // ------------------------------------------------------------
  get selectedCards(): KanbanCard[] {
    return Array.from(this.selectedCardsMap.values());
  }

  isCardSelected(id: string): boolean {
    return this.selectedCardsMap.has(id);
  }

  toggleCardSelection(card: KanbanCard, event: Event): void {
    const checkbox = event.target as HTMLInputElement;
    if (checkbox.checked) {
      this.selectedCardsMap.set(card.id, card);
    } else {
      this.selectedCardsMap.delete(card.id);
    }
  }

  removerCardDoLote(card: KanbanCard): void {
    this.selectedCardsMap.delete(card.id);
  }

  limparSelecao(): void {
    this.selectedCardsMap.clear();
  }

  abrirModalLote(): void {
    if (this.selectedCards.length > 0) {
      this.isModalLoteOpen = true;
    }
  }

  fecharModalLote(): void {
    this.isModalLoteOpen = false;
  }

  onLoteEnviado(): void {
    this.limparSelecao();
    this.carregarPendencias();
  }
}
