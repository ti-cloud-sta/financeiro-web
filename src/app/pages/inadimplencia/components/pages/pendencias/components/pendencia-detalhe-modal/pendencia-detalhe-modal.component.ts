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
      this.gerarDadosMock(this.card);
      this.carregarTratativas();
      this.carregarHistorico();
    }
    if (changes['isOpen'] && this.isOpen) {
      this.activeTab = 'tratativa';
    }
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
    if (t.includes('finalização automática') || t.includes('finalizacao automatica')) {
      return { icone: 'fa-solid fa-flag-checkered', cor: 'success' };
    }
    if (t.includes('importada')) return { icone: 'fa-solid fa-file-circle-plus', cor: 'primary' };
    if (t.includes('fase')) return { icone: 'fa-solid fa-shuffle', cor: 'info' };
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
  // Geração dos dados mocados a partir do card clicado
  // ------------------------------------------------------------
  private gerarDadosMock(card: KanbanCard) {
    const seed = this.seedFromId(card.id);
    const hoje = new Date();

    const dataEmissao = this.subDias(hoje, 30 + (seed % 20));
    const dataEntrega = card.dtVencimento ? this.subDias(card.dtVencimento, 3 + (seed % 5)) : null;
    const valorOriginal = 500 + (seed % 15000) + 0.9;
    const saldo = card.status === 'ACORDO' || card.status === 'COMISSAO'
      ? valorOriginal * 0.6
      : valorOriginal;

    this.detalhe = {
      codigoUnidade: [101, 104, 106][seed % 3].toString(),
      especie: 'DP',
      serie: (1 + (seed % 4)).toString(),
      titulo: card.title,
      parcela: '01',
      codigoCliente: (450000 + seed).toString(),
      nomeCliente: card.clientName,
      portador: (10000 + (seed % 90000)).toString(),
      dataEmissao,
      dataEntrega,
      dataVencimento: card.dtVencimento,
      valorOriginal,
      saldo,
      fase: this.faseLabel(card)
    };

    this.statusSelecionado = this.statusOptions.includes(card.status) ? card.status : this.statusOptions[0];

    // Tratativas vêm da API (ver carregarTratativas) - aqui só reseta o formulário.
    this.novaTratativa = '';
    this.editingTratativaIndex = null;

    this.mensagens = [
      {
        id: 1,
        autor: card.clientName,
        iniciais: this.iniciais(card.clientName),
        minhaMensagem: false,
        data: this.subDias(hoje, 4),
        assunto: `Título ${card.title} em aberto`,
        corpo: 'Boa tarde! Recebemos a notificação sobre o título em aberto. Podem nos confirmar o valor atualizado e a forma de pagamento?',
        anexos: []
      },
      {
        id: 2,
        autor: 'Camila Rocha',
        iniciais: 'CR',
        minhaMensagem: true,
        data: this.subDias(hoje, 4),
        corpo: 'Boa tarde! Segue em anexo o boleto atualizado com o valor corrigido até a data de hoje. Qualquer dúvida estou à disposição.',
        anexos: ['boleto_atualizado.pdf']
      },
      {
        id: 3,
        autor: card.clientName,
        iniciais: this.iniciais(card.clientName),
        minhaMensagem: false,
        data: this.subDias(hoje, 2),
        corpo: 'Recebido, obrigado! Vamos providenciar o pagamento até sexta-feira.',
        anexos: []
      }
    ];

    // Histórico vem da API (ver carregarHistorico) - permanece mocado só até lá ser chamado.
  }

  private faseLabel(card: KanbanCard): string {
    const map: Record<string, string> = {
      danger: 'PENDENCIAS',
      warning: 'LOGISTICA',
      info: 'FISCAL',
      primary: 'COMERCIAL',
      secondary: 'FINANCEIRO',
      success: 'FINALIZADO'
    };
    return map[card.statusColor] || 'PENDENCIAS';
  }

  private seedFromId(id: string): number {
    let hash = 0;
    for (let i = 0; i < id.length; i++) {
      hash = (hash * 31 + id.charCodeAt(i)) % 100000;
    }
    return Math.abs(hash);
  }

  private subDias(data: Date, dias: number): Date {
    const d = new Date(data);
    d.setDate(d.getDate() - dias);
    return d;
  }

  private iniciais(nome: string): string {
    const partes = nome.trim().split(/\s+/);
    if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
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
