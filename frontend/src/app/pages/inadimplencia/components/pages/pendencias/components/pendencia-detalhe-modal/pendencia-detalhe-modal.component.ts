import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../../../../../../shared/components/modal/modal.component';
import { ButtonComponent } from '../../../../../../../shared/components/button/button.component';
import { AvatarComponent } from '../../../../../../../shared/components/avatar/avatar.component';
import { ConfirmModalComponent } from '../../../../../../../shared/components/confirm-modal/confirm-modal.component';
import { ImportacoesService, TratativaApi, HistoricoApi, MensagemThreadApi } from '../../../../../../../core/services/importacoes.service';
import { GoogleAuthService } from '../../../../../../../core/services/google-auth.service';
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
  'ACORDO',
  'AD',
  'AN',
  'ANALISAR',
  'ATRASADO',
  'COMISSAO',
  'DES',
  'DEVOLUCAO',
  'EXPORTACAO',
  'MARTINS',
  'MERCADINHO',
  'OK',
  'PERDAS',
  'PR',
  'PRORROGADO',
  'PROTESTADO',
  'RJ',
  'SEM DATA DE ENTREGA'
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
  imports: [CommonModule, FormsModule, ModalComponent, ButtonComponent, AvatarComponent, ConfirmModalComponent],
  templateUrl: './pendencia-detalhe-modal.component.html',
  styleUrl: './pendencia-detalhe-modal.component.scss'
})
export class PendenciaDetalheModalComponent implements OnChanges {
  private importacoesService = inject(ImportacoesService);
  readonly googleAuthService = inject(GoogleAuthService);

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
  // Aba Mensagens (chat + composição de e-mail com Gmail OAuth)
  // ------------------------------------------------------------
  mensagens: MensagemChat[] = [];
  composeAssunto = '';
  composeDestinatarios = '';
  composeCopias: string[] = [];
  composeCopiaInput = '';
  arquivosSelecionados: File[] = [];
  isEnviandoEmail = false;
  @ViewChild('composeBody') composeBodyRef?: ElementRef<HTMLDivElement>;
  @ViewChild('anexoInput') anexoInputRef?: ElementRef<HTMLInputElement>;

  /**
   * URL pública da assinatura — deve ser acessível externamente para que
   * clientes de e-mail (Gmail, Outlook, etc.) consigam carregar a imagem.
   * Base64 é bloqueada por muitos clientes por políticas de segurança.
   */
  readonly ASSINATURA_URL = 'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjFFw0P_XxmH9v5vpY_xD7PMIP1q2rv_5mwb3CaGqd5rnz3ie-wGL7D8PieowH1fAoQt9AhuT2ehoXRV8AAErbImaEhVWn_qKwytXXoEd5QUK4Ms_fSEOZ7cJTJXmr90qTmNbbj8AcZ7-oBBwH0OXObMEr6wg6UXfzxgf2ibk8vh6fRGNLl7RRsxA_Jm9k/s1600/Composi%C3%A7%C3%A3o-1-TANIA.gif';
  /** Flag para avisar quando a assinatura não pôde ser carregada no editor */
  assinaturaComErro = false;

  // Modais de confirmação/alerta (Design System / No native alert/confirm)
  alertaModalOpen = false;
  alertaTitulo = '';
  alertaMensagem = '';
  alertaVariant: 'primary' | 'danger' | 'success' = 'primary';
  confirmarDesconectarOpen = false;

  // ------------------------------------------------------------
  // Aba Histórico
  // ------------------------------------------------------------
  historico: EventoHistorico[] = [];
  isLoadingHistorico = false;

  // ------------------------------------------------------------
  // Thread de mensagens (Gmail API)
  // ------------------------------------------------------------
  isLoadingMensagens = false;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['card'] && this.card) {
      this.preencherDados(this.card);
      this.carregarTratativas();
      this.carregarHistorico();
      if (this.activeTab === 'mensagens') {
        this.googleAuthService.verificarStatus().subscribe();
        this.carregarMensagensThread();
      }
    }
    if (changes['isOpen'] && this.isOpen) {
      this.activeTab = 'tratativa';
      this.assinaturaComErro = false;
      this.googleAuthService.verificarStatus().subscribe();
    }
  }

  setTab(tab: PendenciaTab) {
    this.activeTab = tab;
    if (tab === 'mensagens') {
      this.googleAuthService.verificarStatus().subscribe();
      this.carregarMensagensThread();
      if (!this.composeAssunto && this.card) {
        this.composeAssunto = `Cobrança - Título ${this.card.title} - ${this.card.fullClientName || this.card.clientName}`;
      }
      // Aguarda o próximo ciclo para garantir que @else if já renderizou o DOM
      setTimeout(() => this.inserirAssinatura());
    } else if (tab === 'historico') {
      this.carregarHistorico();
    } else if (tab === 'tratativa') {
      this.carregarTratativas();
    }
  }

  /**
   * Insere a assinatura como <img> com URL pública no editor contenteditable.
   * Adiciona handler onerror para avisar o usuário se a imagem não carregar.
   */
  private inserirAssinatura() {
    if (!this.composeBodyRef || !this.card) return;
    const el = this.composeBodyRef.nativeElement;
    const htmlAtual = el.innerHTML.trim();

    // Identifica se a assinatura já foi inserida pela presença da URL
    const assinaturaJaPresente = htmlAtual.includes(this.ASSINATURA_URL);
    if (assinaturaJaPresente) return;

    const assinaturaHtml = `<br><br><img
      src="${this.ASSINATURA_URL}"
      alt="Assinatura"
      style="max-width: 580px; width: 100%; height: auto; display: block;"
      onerror="this.style.display='none'; document.dispatchEvent(new CustomEvent('assinatura-erro'));"
    >`;

    if (!htmlAtual || htmlAtual === '<br>' || htmlAtual === '<div><br></div>') {
      el.innerHTML = assinaturaHtml;
    } else {
      el.innerHTML = htmlAtual + assinaturaHtml;
    }

    // Escuta o evento de erro disparado pelo onerror inline
    const handler = () => {
      this.assinaturaComErro = true;
      document.removeEventListener('assinatura-erro', handler);
    };
    document.addEventListener('assinatura-erro', handler, { once: true });
  }

  aplicarTemplate(tipo: 'cobranca' | 'recobranca' | 'protesto' | 'sem_data' | 'devolucao') {
    if (!this.composeBodyRef || !this.card) return;

    const el = this.composeBodyRef.nativeElement;
    const valorFormatado = (this.card.valorSaldo || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const dataVenc = this.card.dtVencimento ? new Date(this.card.dtVencimento).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : '-';
    const parcela = this.card.parccela || '-';
    const assinaturaHtml = `<br><br><img src="${this.ASSINATURA_URL}" alt="Assinatura" style="max-width: 580px; width: 100%; height: auto; display: block;">`;

    let textoHtml = '';

    switch (tipo) {
      case 'cobranca':
        textoHtml = `Prezado(a) cliente <b>${this.card.fullClientName || this.card.clientName}</b>,<br><br>
Consta em nosso sistema o título <b>${this.card.title}</b> (Parcela: ${parcela}) no valor de <b>${valorFormatado}</b>, com vencimento original em <b>${dataVenc}</b>, que se encontra pendente de regularização.<br><br>
Caso o pagamento já tenha sido efetuado, por favor, desconsidere esta mensagem e nos envie o comprovante para que possamos baixar no sistema. Se houve algum contratempo ou dificuldade para emissão do boleto, estamos à disposição para ajudar.<br><br>
Atenciosamente,${assinaturaHtml}`;
        break;
      case 'recobranca':
        textoHtml = `Prezado(a) cliente <b>${this.card.fullClientName || this.card.clientName}</b>,<br><br>
Até o momento, não identificamos o pagamento referente ao título <b>${this.card.title}</b> (Parcela: ${parcela}) no valor de <b>${valorFormatado}</b>, vencido no dia <b>${dataVenc}</b>.<br><br>
Pedimos a gentileza de nos enviar o comprovante caso o pagamento já tenha ocorrido. Caso contrário, solicitamos uma previsão para a regularização desta pendência ou que entre em contato conosco para verificarmos uma possível negociação.<br><br>
No aguardo de um retorno,<br>Atenciosamente,${assinaturaHtml}`;
        break;
      case 'protesto':
        textoHtml = `Prezado(a) cliente <b>${this.card.fullClientName || this.card.clientName}</b>,<br><br>
Informamos que o título <b>${this.card.title}</b> (Parcela: ${parcela}), no valor de <b>${valorFormatado}</b> e vencido em <b>${dataVenc}</b>, continua pendente de pagamento em nosso sistema.<br><br>
Como não obtivemos retorno nas tentativas de contato anteriores, comunicamos que, caso a pendência não seja regularizada (ou não nos seja enviado o comprovante) nos próximos 2 dias úteis, o título será automaticamente encaminhado ao cartório para <b>protesto</b> e inclusão nos órgãos de proteção ao crédito.<br><br>
Para evitar os transtornos e custas cartoriais, solicitamos a regularização imediata.<br><br>
Atenciosamente,${assinaturaHtml}`;
        break;
      case 'sem_data':
        textoHtml = `Prezados do setor Logística,<br><br>
Estamos realizando um acompanhamento de nossa carteira e verificamos que a mercadoria referente ao título <b>${this.card.title}</b> (Valor: <b>${valorFormatado}</b>) ainda não possui a confirmação e data exata de entrega registrada em nosso sistema.<br><br>
Poderia, por gentileza, nos confirmar quando será entregue? Essa informação é muito importante para nosso controle de qualidade e faturamento.<br><br>
Agradecemos a colaboração.<br>Atenciosamente,${assinaturaHtml}`;
        break;
      case 'devolucao':
        textoHtml = `Prezados do setor Logística,<br><br>
Identificamos em nosso sistema que houve uma ocorrência de devolução envolvendo a nota fiscal/título <b>${this.card.title}</b> no valor de <b>${valorFormatado}</b>.<br><br>
Para que possamos dar andamento correto aos trâmites financeiros internamente, solicitamos que nos informe brevemente a posição referente a essa nota.<br><br>
Ficamos à disposição para esclarecimentos.<br>Atenciosamente,${assinaturaHtml}`;
        break;
    }

    el.innerHTML = textoHtml;
  }

  mostrarAlerta(titulo: string, mensagem: string, variant: 'primary' | 'danger' | 'success' = 'primary') {
    this.alertaTitulo = titulo;
    this.alertaMensagem = mensagem;
    this.alertaVariant = variant;
    this.alertaModalOpen = true;
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

  private mensagensSub?: any;

  carregarMensagensThread() {
    if (!this.card) return;
    const idNf = Number(this.card.id);
    this.isLoadingMensagens = true;
    
    if (this.mensagensSub) {
      this.mensagensSub.unsubscribe();
    }
    
    this.mensagensSub = this.importacoesService.listarMensagensPendencia(idNf).subscribe({
      next: (msgs: MensagemThreadApi[]) => {
        this.isLoadingMensagens = false;
        this.mensagens = msgs.map(m => this.mapearMensagemApi(m));
      },
      error: (err) => {
        this.isLoadingMensagens = false;
        console.error('Erro ao carregar mensagens:', err);
      }
    });
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
      anexos: m.anexos.map(a => a.nome)
    };
  }

  private extrairNomeEmail(de: string): string {
    if (!de) return 'Desconhecido';
    // "Nome Sobrenome <email@domain.com>" → "Nome Sobrenome"
    const match = de.match(/^([^<]+)</);
    if (match) return match[1].trim();
    return de.trim();
  }

  private obterIniciais(nome: string): string {
    if (!nome) return 'EU';
    const partes = nome.trim().split(/\s+/);
    if (partes.length === 1) return partes[0].substring(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
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

  onStatusChange() {
    if (!this.card) return;
    const novoStatus = this.statusSelecionado;

    this.salvandoStatus = true;
    this.importacoesService.alterarStatusPendencia(Number(this.card.id), novoStatus).subscribe({
      next: (res) => {
        this.salvandoStatus = false;
        if (this.card) {
          this.card.status = res.status;
          this.card.statusColor = this.detalhe?.fase === 'FINALIZADO' && res.status === 'OK' ? 'success' : 'warning';
        }
        this.atualizado.emit();
        this.carregarHistorico();
      },
      error: (err) => {
        this.salvandoStatus = false;
        console.error('Erro ao alterar status da pendência:', err);
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
      nomeCliente: card.fullClientName || card.clientName,
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

    // Reset de Mensagens e Compose
    this.mensagens = [];
    this.composeAssunto = `Cobrança - Título ${card.title} - ${card.fullClientName || card.clientName}`;
    this.composeDestinatarios = '';
    this.composeCopias = [];
    this.composeCopiaInput = '';
    this.arquivosSelecionados = [];
    if (this.composeBodyRef) {
      this.composeBodyRef.nativeElement.innerHTML = '';
    }

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
  // Ações da aba Mensagens (Google OAuth e Envio de E-mail)
  // ------------------------------------------------------------
  aplicarFormatacao(comando: 'bold' | 'italic' | 'underline' | 'insertUnorderedList') {
    if (this.composeBodyRef) {
      const el = this.composeBodyRef.nativeElement;
      if (document.activeElement !== el && !el.contains(document.activeElement)) {
        el.focus();
      }
      document.execCommand(comando, false);
    }
  }

  triggerAnexo() {
    this.anexoInputRef?.nativeElement.click();
  }

  onAnexoSelecionado(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      Array.from(input.files).forEach(f => {
        if (!this.arquivosSelecionados.some(existente => existente.name === f.name && existente.size === f.size)) {
          this.arquivosSelecionados.push(f);
        }
      });
      input.value = '';
    }
  }

  removerArquivo(index: number) {
    this.arquivosSelecionados.splice(index, 1);
  }

  formatarTamanhoArquivo(bytes: number): string {
    if (!bytes || bytes <= 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  async conectarGoogle() {
    try {
      await this.googleAuthService.iniciarAutorizacaoPopup();
      this.mostrarAlerta(
        'Google Conectado',
        'Sua conta do Gmail foi autorizada com sucesso! Agora você já pode enviar mensagens diretamente.',
        'success'
      );
    } catch (err: any) {
      console.error('Erro ao conectar Google:', err);
      this.mostrarAlerta('Falha na Autorização', err.message || 'Não foi possível autorizar o Gmail.', 'danger');
    }
  }

  abrirConfirmarDesconexao() {
    this.confirmarDesconectarOpen = true;
  }

  desconectarGoogle() {
    this.confirmarDesconectarOpen = false;
    this.googleAuthService.desconectar().subscribe({
      next: () => {
        this.mostrarAlerta('Conta Desconectada', 'Sua conta do Gmail foi desconectada com sucesso.', 'primary');
      },
      error: (err) => {
        const msg = err.error?.detail || err.message || 'Erro ao desconectar conta Google.';
        this.mostrarAlerta('Erro ao Desconectar', msg, 'danger');
      }
    });
  }

  enviarMensagem() {
    if (!this.card || this.isEnviandoEmail) return;

    const corpo = this.composeBodyRef?.nativeElement.innerHTML?.trim() || '';
    if (!corpo || corpo === '<br>' || corpo === '<div><br></div>') {
      this.mostrarAlerta('Mensagem Vazia', 'Por favor, escreva o conteúdo da mensagem antes de enviar.', 'primary');
      return;
    }

    if (!this.composeDestinatarios.trim()) {
      this.mostrarAlerta('Destinatário Ausente', 'Por favor, informe ao menos um e-mail no campo "Para (destinatários)".', 'primary');
      return;
    }

    if (!this.composeAssunto.trim()) {
      this.mostrarAlerta('Assunto Obrigatório', 'Por favor, preencha o assunto do e-mail.', 'primary');
      return;
    }

    // Se o usuário ainda não autorizou o Gmail, abre o popup de autorização
    if (!this.googleAuthService.isConectado()) {
      this.googleAuthService.iniciarAutorizacaoPopup()
        .then(() => this._dispararEnvio(corpo))
        .catch(() => this.mostrarAlerta('Autorização Necessária', 'É obrigatório conectar sua conta do Google antes de enviar e-mails.', 'danger'));
      return;
    }

    this._dispararEnvio(corpo);
  }

  /** Monta o FormData e faz o POST. O corpo já contém a URL pública da assinatura — nenhuma conversão necessária. */
  private _dispararEnvio(corpo: string) {
    if (!this.card) return;

    this.isEnviandoEmail = true;

    const formData = new FormData();
    formData.append('destinatarios', this.composeDestinatarios.trim());
    formData.append('assunto', this.composeAssunto.trim());
    formData.append('corpo', corpo);
    const copiaFinal = this.obterCopiaFinal();
    if (copiaFinal) {
      formData.append('copia', copiaFinal);
    }
    for (const file of this.arquivosSelecionados) {
      formData.append('anexos', file, file.name);
    }

    const idNf = Number(this.card.id);
    this.importacoesService.enviarEmailPendencia(idNf, formData).subscribe({
      next: () => {
        this.isEnviandoEmail = false;

        // Limpa os campos do formulário
        this.composeAssunto = '';
        this.composeDestinatarios = '';
        this.composeCopias = [];
        this.composeCopiaInput = '';
        this.arquivosSelecionados = [];
        if (this.composeBodyRef) {
          this.composeBodyRef.nativeElement.innerHTML = '';
          this.inserirAssinatura();
        }

        // Recarrega o thread completo (inclui a mensagem recém enviada)
        this.carregarMensagensThread();
        this.carregarHistorico();

        this.mostrarAlerta('E-mail Enviado!', 'A mensagem foi enviada com sucesso utilizando sua conta do Gmail.', 'success');
      },
      error: (err) => {
        this.isEnviandoEmail = false;
        console.error('Erro ao enviar e-mail:', err);
        const detalhe = err.error?.detail || err.message || 'Falha ao enviar e-mail pelo Gmail.';
        this.mostrarAlerta('Falha no Envio', detalhe, 'danger');
      }
    });
  }

  // ------------------------------------------------------------
  // Métodos de Gerenciamento de Chips de Cópia (Cc)
  // ------------------------------------------------------------
  adicionarCopia(): void {
    const raw = this.composeCopiaInput ? this.composeCopiaInput.trim() : '';
    if (!raw) return;

    const pedacos = raw.split(/[,;\n\r]+/);
    for (const p of pedacos) {
      const email = p.trim();
      if (email && !this.composeCopias.includes(email)) {
        this.composeCopias.push(email);
      }
    }
    this.composeCopiaInput = '';
  }

  removerCopia(index: number): void {
    if (index >= 0 && index < this.composeCopias.length) {
      this.composeCopias.splice(index, 1);
    }
  }

  aoPressionarTeclaCopia(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ',' || event.key === ';') {
      event.preventDefault();
      this.adicionarCopia();
    } else if (event.key === 'Backspace' && !this.composeCopiaInput && this.composeCopias.length > 0) {
      this.composeCopias.pop();
    }
  }

  aoColarCopia(event: ClipboardEvent): void {
    const texto = event.clipboardData?.getData('text');
    if (texto && /[,;\n\r\s]/.test(texto)) {
      event.preventDefault();
      const pedacos = texto.split(/[,;\n\r\s]+/);
      for (const p of pedacos) {
        const email = p.trim();
        if (email && !this.composeCopias.includes(email)) {
          this.composeCopias.push(email);
        }
      }
    }
  }

  focarInputCopia(inputEl: HTMLInputElement): void {
    inputEl?.focus();
  }

  emailValido(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  obterCopiaFinal(): string {
    this.adicionarCopia();
    return this.composeCopias.join(', ');
  }
}
