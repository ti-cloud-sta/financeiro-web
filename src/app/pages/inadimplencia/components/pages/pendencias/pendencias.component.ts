import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FlatpickrModule } from 'angularx-flatpickr';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';
import { ImportacoesService, PendenciaKanban, JanelaRegraDia } from '../../../../../core/services/importacoes.service';
import { PendenciaDetalheModalComponent } from './components/pendencia-detalhe-modal/pendencia-detalhe-modal.component';

export interface KanbanCard {
  id: string;
  title: string;
  status: string;
  statusColor: string;
  clientName: string;
  dtVencimento: Date | null;
  leadTimeDays: number | null;
}

export interface KanbanColumn {
  id: string;
  title: string;
  icon: string;
  colorClass: string;
  cards: KanbanCard[];
}

type PeriodShortcut = 'vencidas' | 'ultimo-bimestre' | 'ultimo-semestre' | 'este-ano' | 'ano-passado' | 'regra-dia' | 'personalizado';

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
  imports: [CommonModule, FormsModule, FlatpickrModule, PendenciaDetalheModalComponent],
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
  isLoading = false;

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
    this.carregarPendencias();
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
        statusColor: coluna.colorClass,
        clientName: this.sliceClientName(item.clienteNome),
        dtVencimento: item.dtVencimento ? new Date(item.dtVencimento + 'T00:00:00') : null,
        leadTimeDays: this.calcularDiasDesdeImportacao(item.createdAt)
      });
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

  get statusOptions(): string[] {
    const statuses = this.columns.flatMap(col => col.cards.map(card => card.status));
    return Array.from(new Set(statuses));
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
        cards: column.cards.filter(card => this.cardMatchesFilters(card))
      }));
  }

  private cardMatchesFilters(card: KanbanCard): boolean {
    // O filtro de período (data) já é aplicado pelo backend em carregarPendencias() -
    // aqui só resta o filtro de status, que continua sendo client-side sobre o board.
    return !this.statusFiltro || card.status === this.statusFiltro;
  }

  onDataInicioChange() {
    if (this.dataInicio && this.dataFim && this.dataInicio > this.dataFim) {
      this.dataFim = this.dataInicio;
    }
    this.activePeriodShortcut = 'personalizado';
    this.carregarPendencias();
  }

  onDataFimChange() {
    this.activePeriodShortcut = 'personalizado';
    this.carregarPendencias();
  }

  onShortcutSelectChange(val: PeriodShortcut) {
    if (!val || val === 'personalizado') return;
    if (val === 'regra-dia') {
      this.aplicarRegraDia();
      return;
    }
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

  selecionarAtalhoPeriodo(shortcut: Exclude<PeriodShortcut, 'personalizado' | 'regra-dia' | 'vencidas'>) {
    const today = new Date();

    const getPastDate = (monthsAgo: number) => {
      const d = new Date();
      d.setMonth(d.getMonth() - monthsAgo);
      return d;
    };

    if (shortcut === 'ultimo-bimestre') {
      this.dataInicio = getPastDate(2);
      this.dataFim = today;
    } else if (shortcut === 'ultimo-semestre') {
      this.dataInicio = getPastDate(6);
      this.dataFim = today;
    } else if (shortcut === 'este-ano') {
      this.dataInicio = new Date(today.getFullYear(), 0, 1);
      this.dataFim = new Date(today.getFullYear(), 11, 31);
    } else if (shortcut === 'ano-passado') {
      this.dataInicio = new Date(today.getFullYear() - 1, 0, 1);
      this.dataFim = new Date(today.getFullYear() - 1, 11, 31);
    }

    this.activePeriodShortcut = shortcut;
  }

  aplicarRegraDia() {
    if (!this.regraDiaAplicavel || !this.regraDiaInicio || !this.regraDiaFim) return;
    this.dataInicio = new Date(this.regraDiaInicio + 'T00:00:00');
    this.dataFim = new Date(this.regraDiaFim + 'T00:00:00');
    this.activePeriodShortcut = 'regra-dia';
    this.carregarPendencias();
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

      // Remove da coluna de origem
      const sourceCol = this.columns.find(c => c.id === idColunaOrigem);
      if (sourceCol) {
        sourceCol.cards = sourceCol.cards.filter(c => c.id !== card.id);
      }

      // Adiciona na coluna de destino (busca a coluna real, já que o template itera sobre a versão filtrada)
      const destCol = this.columns.find(c => c.id === idColunaDestino);
      if (destCol) {
        card.statusColor = destCol.colorClass;
        destCol.cards.push(card);
      }

      // Persiste a mudança de fase (id da coluna = fase em maiúsculas). Se falhar, desfaz
      // a movimentação visual e devolve o card pra coluna de origem.
      this.importacoesService.alterarFasePendencia(Number(card.id), idColunaDestino.toUpperCase()).subscribe({
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
  }
}
