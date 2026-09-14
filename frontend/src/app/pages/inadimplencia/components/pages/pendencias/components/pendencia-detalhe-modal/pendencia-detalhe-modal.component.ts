import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../../../../../../shared/components/modal/modal.component';
import { ButtonComponent } from '../../../../../../../shared/components/button/button.component';
import { AvatarComponent } from '../../../../../../../shared/components/avatar/avatar.component';
import { ImportacoesService, TratativaApi, HistoricoApi } from '../../../../../../../core/services/importacoes.service';
import { KanbanCard } from '../../pendencias.component';

export type PendenciaTab = 'tratativa' | 'mensagens' | 'historico';

export interface PendenciaDetalhe {
  codigoUnidade: string;
  especie: string;
  serie: string;
  titulo: string;
  parcela: string;
  codigoCliente: string;
  nomeCliente: string;
  portador: string;
  dataEmissao: Date;
  dataEntrega: Date | null;
  dataVencimento: Date | null;
  valorOriginal: number;
  saldo: number;
  fase: string;
}

export interface TratativaItem {
  id: number;
  data: Date;
  autor: string;
  texto: string;
}

export interface MensagemChat {
  id: number;
  autor: string;
  iniciais: string;
  minhaMensagem: boolean;
  data: Date;
  assunto?: string;
  corpo: string;
  anexos: string[];
}

export interface EventoHistorico {
  data: Date;
  tipo: string;
  observacao: string;
  icone: string;
  cor: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'secondary';
}

export const STATUS_OPTIONS: string[] = [
  'DEVOLUCAO',
  'SEM DATA DE ENTREGA',
  'ACORDO',
  'COMISSAO',
  'EXPORTACAO',
  'MARTINS',
  'MERCADINHO',
  'CART-DES',
  'ATRASADO',
  'ANALISAR',
  'PROTESTADO',
  'PERDAS'
];

// Mesmas fases usadas como colunas do Kanban de Pendências
export const FASE_OPTIONS: string[] = [
  'PENDENCIAS',
  'LOGISTICA',
  'FISCAL',
  'COMERCIAL',
  'FINANCEIRO',
  'FINALIZADO'
];

@Component({
  selector: 'app-pendencia-detalhe-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, ButtonComponent, AvatarComponent],
  templateUrl: './pendencia-detalhe-modal.component.html',
  styleUrl: './pendencia-detalhe-modal.component.scss'
})
export class PendenciaDetalheModalComponent implements OnChanges {
  private importacoesService = inject(ImportacoesService);

  @Input() isOpen = false;
  @Input() card: KanbanCard | null = null;

  @Output() closed = new EventEmitter<void>();
  // Emitido quando fase/status são alterados com sucesso, para o board recarregar as colunas.
  @Output() atualizado = new EventEmitter<void>();

  statusOptions = STATUS_OPTIONS;
  faseOptions = FASE_OPTIONS;
  activeTab: PendenciaTab = 'tratativa';

  detalhe: PendenciaDetalhe | null = null;
  statusSelecionado = '';
  salvandoFase = false;
  salvandoStatus = false;

  // ------------------------------------------------------------
  // Aba Tratativa
  // ------------------------------------------------------------
  novaTratativa = '';
  tratativas: TratativaItem[] = [];
  editingTratativaIndex: number | null = null;
  isLoadingTratativas = false;
  isSalvandoTratativa = false;

  // ------------------------------------------------------------
  // Aba Mensagens (chat + composição de e-mail)
  // ------------------------------------------------------------
  mensagens: MensagemChat[] = [];
  composeAssunto = '';
  composeDestinatarios = '';
  composeCopia = '';
  composeAnexos: string[] = [];
  @ViewChild('composeBody') composeBodyRef?: ElementRef<HTMLDivElement>;
  @ViewChild('anexoInput') anexoInputRef?: ElementRef<HTMLInputElement>;

  // ------------------------------------------------------------
  // Aba Histórico
  // ------------------------------------------------------------
  historico: EventoHistorico[] = [];
  isLoadingHistorico = false;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['card'] && this.card) {
      this.preencherDados(this.card);
      this.carregarTratativas();
      this.carregarHistorico();
    }
    if (changes['isOpen'] && this.isOpen) {
      this.activeTab = 'tratativa';
    }
  }

  get faseColor(): string {
    if (!this.detalhe) return 'secondary';
    const f = (this.detalhe.fase || '').toLowerCase();
    if (f === 'pendencias') return 'danger';
    if (f === 'logistica') return 'warning';
    if (f === 'fiscal') return 'info';
    if (f === 'comercial') return 'primary';
    if (f === 'financeiro') return 'secondary';
    if (f === 'finalizado') return 'success';
    return 'secondary';
  }

  carregarHistorico() {
    if (!this.card) return;
    const idNf = Number(this.card.id);
    this.isLoadingHistorico = true;
    this.importacoesService.listarHistoricoPendencia(idNf).subscribe({
      next: (itens) => {
        this.isLoadingHistorico = false;
        this.historico = itens.map(h => this.mapearHistoricoApi(h));
      },
      error: (err) => {
        this.isLoadingHistorico = false;
        console.error('Erro ao carregar histórico:', err);
        this.historico = [];
      }
    });
  }

  private mapearHistoricoApi(h: HistoricoApi): EventoHistorico {
    const { icone, cor } = this.iconeCorPorTipo(h.tipo);
    return {
      data: h.createdAt ? new Date(h.createdAt) : new Date(),
      tipo: h.tipo || '-',
      observacao: h.observacao || '',
      icone,
      cor
    };
  }

  private iconeCorPorTipo(tipo: string | null): { icone: string; cor: EventoHistorico['cor'] } {
    const t = (tipo || '').toLowerCase();
    if (t.includes('finaliza') || t.includes('resolu')) {
      return { icone: 'fa-solid fa-check-circle', cor: 'success' };
    }
    if (t.includes('prorrogad')) return { icone: 'fa-regular fa-calendar-plus', cor: 'warning' };
    if (t.includes('importada')) return { icone: 'fa-solid fa-file-circle-plus', cor: 'primary' };
    if (t.includes('fase') || t.includes('classifica')) return { icone: 'fa-solid fa-shuffle', cor: 'info' };
    if (t.includes('status')) return { icone: 'fa-solid fa-flag', cor: 'warning' };
    if (t.includes('tratativa')) return { icone: 'fa-solid fa-headset', cor: 'success' };
    return { icone: 'fa-solid fa-circle-info', cor: 'secondary' };
  }

  carregarTratativas() {
    if (!this.card) return;
    const idNf = Number(this.card.id);
    this.isLoadingTratativas = true;
    this.importacoesService.listarTratativas(idNf).subscribe({
      next: (itens) => {
        this.isLoadingTratativas = false;
        this.tratativas = itens.map(t => this.mapearTratativaApi(t));
      },
      error: (err) => {
        this.isLoadingTratativas = false;
        console.error('Erro ao carregar tratativas:', err);
        this.tratativas = [];
      }
    });
  }

  private mapearTratativaApi(t: TratativaApi): TratativaItem {
    return {
      id: t.idtratativas,
      data: t.createdAt ? new Date(t.createdAt) : new Date(),
      autor: t.autor || 'Usuário',
      texto: t.conteudo
    };
  }

  setTab(tab: PendenciaTab) {
    this.activeTab = tab;
  }

  close() {
    this.isOpen = false;
    this.closed.emit();
  }

  onFaseChange(novaFase: string) {
    if (!this.detalhe || !this.card) return;
    const faseAnterior = this.detalhe.fase;
    if (faseAnterior === novaFase) return;

    this.detalhe.fase = novaFase;
    this.salvandoFase = true;
    this.importacoesService.alterarFasePendencia(Number(this.card.id), novaFase).subscribe({
      next: () => {
        this.salvandoFase = false;
        this.atualizado.emit();
        this.carregarHistorico();
      },
      error: (err) => {
        this.salvandoFase = false;
        console.error('Erro ao alterar fase da pendência:', err);
        if (this.detalhe) this.detalhe.fase = faseAnterior;
      }
    });
  }

  onStatusChange(novoStatus: string) {
    if (!this.card) return;
    const statusAnterior = this.statusSelecionado;
    if (statusAnterior === novoStatus) return;

    this.statusSelecionado = novoStatus;
    this.salvandoStatus = true;
    this.importacoesService.alterarStatusPendencia(Number(this.card.id), novoStatus).subscribe({
      next: () => {
        this.salvandoStatus = false;
        this.atualizado.emit();
        this.carregarHistorico();
      },
      error: (err) => {
        this.salvandoStatus = false;
        console.error('Erro ao alterar status da pendência:', err);
        this.statusSelecionado = statusAnterior;
      }
    });
  }

  // ------------------------------------------------------------
  // Geração dos dados reais a partir do card clicado
  // ------------------------------------------------------------
  private preencherDados(card: KanbanCard) {
    const hoje = new Date();

    this.detalhe = {
      codigoUnidade: card.idUnidade?.toString() || '-',
      especie: card.especie || '-',
      serie: card.serie || '-',
      titulo: card.title,
      parcela: card.parccela || '-',
      codigoCliente: card.idCliente?.toString() || '-',
      nomeCliente: card.clientName,
      portador: card.portador || '-',
      dataEmissao: card.dtEmissao || hoje,
      dataEntrega: card.dtEntrega,
      dataVencimento: card.dtVencimento,
      valorOriginal: card.valorOriginal || 0,
      saldo: card.valorSaldo || 0,
      fase: card.fase || '-'
    };

    this.statusSelecionado = this.statusOptions.includes(card.status) ? card.status : this.statusOptions[0];

    // Tratativas vêm da API (ver carregarTratativas) - aqui só reseta o formulário.
    this.novaTratativa = '';
    this.editingTratativaIndex = null;

    // TODO: Mensagens do chat podem vir da API futuramente
    this.mensagens = [];

    // Histórico vem da API (ver carregarHistorico) - permanece mocado só até lá ser chamado.
  }

  // ------------------------------------------------------------
  // Ações da aba Tratativa
  // ------------------------------------------------------------
  registrarTratativa() {
    const texto = this.novaTratativa.trim();
    if (!texto || !this.card || this.isSalvandoTratativa) return;

    this.isSalvandoTratativa = true;

    if (this.editingTratativaIndex !== null) {
      const item = this.tratativas[this.editingTratativaIndex];
      this.importacoesService.editarTratativa(item.id, texto).subscribe({
        next: (atualizada) => {
          this.isSalvandoTratativa = false;
          this.tratativas[this.editingTratativaIndex!] = this.mapearTratativaApi(atualizada);
          this.editingTratativaIndex = null;
          this.novaTratativa = '';
        },
        error: (err) => {
          this.isSalvandoTratativa = false;
          console.error('Erro ao editar tratativa:', err);
        }
      });
    } else {
      this.importacoesService.criarTratativa(Number(this.card.id), texto).subscribe({
        next: (criada) => {
          this.isSalvandoTratativa = false;
          this.tratativas.unshift(this.mapearTratativaApi(criada));
          this.novaTratativa = '';
        },
        error: (err) => {
          this.isSalvandoTratativa = false;
          console.error('Erro ao registrar tratativa:', err);
        }
      });
    }
  }

  editarTratativa(index: number) {
    this.editingTratativaIndex = index;
    this.novaTratativa = this.tratativas[index].texto;
  }

  cancelarEdicaoTratativa() {
    this.editingTratativaIndex = null;
    this.novaTratativa = '';
  }

  // ------------------------------------------------------------
  // Ações da aba Mensagens
  // ------------------------------------------------------------
  aplicarFormatacao(comando: 'bold' | 'italic' | 'underline' | 'insertUnorderedList') {
    this.composeBodyRef?.nativeElement.focus();
    document.execCommand(comando, false);
  }

  triggerAnexo() {
    this.anexoInputRef?.nativeElement.click();
  }

  onAnexoSelecionado(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      Array.from(input.files).forEach(f => this.composeAnexos.push(f.name));
      input.value = '';
    }
  }

  removerAnexo(index: number) {
    this.composeAnexos.splice(index, 1);
  }

  enviarMensagem() {
    const corpo = this.composeBodyRef?.nativeElement.innerHTML?.trim() || '';
    if (!corpo || corpo === '<br>') return;

    this.mensagens.push({
      id: this.mensagens.length + 1,
      autor: 'Você',
      iniciais: 'EU',
      minhaMensagem: true,
      data: new Date(),
      assunto: this.composeAssunto || undefined,
      corpo,
      anexos: [...this.composeAnexos]
    });

    this.composeAssunto = '';
    this.composeDestinatarios = '';
    this.composeCopia = '';
    this.composeAnexos = [];
    if (this.composeBodyRef) {
      this.composeBodyRef.nativeElement.innerHTML = '';
    }
  }
}
