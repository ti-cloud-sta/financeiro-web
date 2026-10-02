import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../../../../../../shared/components/modal/modal.component';
import { ButtonComponent } from '../../../../../../../shared/components/button/button.component';
import { ConfirmModalComponent } from '../../../../../../../shared/components/confirm-modal/confirm-modal.component';
import { ImportacoesService } from '../../../../../../../core/services/importacoes.service';
import { GoogleAuthService } from '../../../../../../../core/services/google-auth.service';
import { KanbanCard } from '../../pendencias.component';

@Component({
  selector: 'app-pendencia-lote-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, ButtonComponent, ConfirmModalComponent],
  templateUrl: './pendencia-lote-modal.component.html',
  styleUrl: './pendencia-lote-modal.component.scss'
})
export class PendenciaLoteModalComponent implements OnChanges {
  private importacoesService = inject(ImportacoesService);
  readonly googleAuthService = inject(GoogleAuthService);

  @Input() isOpen = false;
  @Input() cards: KanbanCard[] = [];

  @Output() closed = new EventEmitter<void>();
  @Output() enviado = new EventEmitter<void>();
  @Output() cardRemovido = new EventEmitter<KanbanCard>();

  // Campos de composição do e-mail
  composeAssunto = '';
  composeDestinatarios = '';
  composeCopias: string[] = [];
  composeCopiaInput = '';
  arquivosSelecionados: File[] = [];
  isEnviandoEmail = false;

  @ViewChild('composeBody') composeBodyRef?: ElementRef<HTMLDivElement>;
  @ViewChild('anexoInput') anexoInputRef?: ElementRef<HTMLInputElement>;

  readonly ASSINATURA_URL = 'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjFFw0P_XxmH9v5vpY_xD7PMIP1q2rv_5mwb3CaGqd5rnz3ie-wGL7D8PieowH1fAoQt9AhuT2ehoXRV8AAErbImaEhVWn_qKwytXXoEd5QUK4Ms_fSEOZ7cJTJXmr90qTmNbbj8AcZ7-oBBwH0OXObMEr6wg6UXfzxgf2ibk8vh6fRGNLl7RRsxA_Jm9k/s1600/Composi%C3%A7%C3%A3o-1-TANIA.gif';
  assinaturaComErro = false;

  // Modais de confirmação/alerta (Design System)
  alertaModalOpen = false;
  alertaTitulo = '';
  alertaMensagem = '';
  alertaVariant: 'primary' | 'danger' | 'success' = 'primary';
  confirmarDesconectarOpen = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isOpen'] && this.isOpen) {
      this.assinaturaComErro = false;
      this.googleAuthService.verificarStatus().subscribe();
      this.sugerirAssunto();
      setTimeout(() => this.inserirAssinatura());
    }
    if (changes['cards'] && this.isOpen) {
      if (!this.composeAssunto) {
        this.sugerirAssunto();
      }
    }
  }

  get valorTotalSaldo(): number {
    return this.cards.reduce((acc, c) => acc + (c.valorSaldo || 0), 0);
  }

  get clientesDistintos(): string[] {
    const set = new Set<string>();
    for (const c of this.cards) {
      const nome = c.fullClientName || c.clientName || 'Cliente';
      set.add(nome);
    }
    return Array.from(set);
  }

  get nomeClienteExibicao(): string {
    const clientes = this.clientesDistintos;
    if (clientes.length === 0) return '-';
    if (clientes.length === 1) return clientes[0];
    return `${clientes[0]} + ${clientes.length - 1} outro(s)`;
  }

  removerTitulo(card: KanbanCard): void {
    this.cardRemovido.emit(card);
  }

  close(): void {
    this.closed.emit();
  }

  sugerirAssunto(tipoTemplate?: 'cobranca' | 'recobranca' | 'protesto' | 'sem_data' | 'devolucao'): void {
    if (this.cards.length === 0) {
      this.composeAssunto = 'Cobrança - Títulos Pendentes';
      return;
    }

    // Helper para extrair e formatar datas de vencimento distintas dos cards selecionados
    const extrairVencimentos = (): string => {
      const datas = Array.from(new Set(
        this.cards
          .filter(c => c.dtVencimento)
          .map(c => new Date(c.dtVencimento!).toLocaleDateString('pt-BR', { timeZone: 'UTC' }))
      ));
      return datas.length > 0 ? datas.join(', ') : '';
    };

    // Se acionado pelo botão de template da Logística
    if (tipoTemplate === 'sem_data') {
      const v = extrairVencimentos();
      this.composeAssunto = v ? `Titulos sem data de entrega - (${v})` : 'Titulos sem data de entrega';
      return;
    }
    if (tipoTemplate === 'devolucao') {
      this.composeAssunto = 'Notas de Devolução pendente';
      return;
    }

    // Se for abertura automática / sincronização de cards
    const ehLogistica = this.cards.some(c => (c.fase || '').toUpperCase() === 'LOGISTICA');
    const ehDevolucao = this.cards.some(c => c.isDevolucao || c.status === 'DEVOLUCAO');
    const semDataEntrega = this.cards.some(c => !c.dtEntrega);

    if ((ehLogistica || ehDevolucao || semDataEntrega) && !tipoTemplate) {
      if (ehDevolucao) {
        this.composeAssunto = 'Notas de Devolução pendente';
        return;
      }
      const v = extrairVencimentos();
      this.composeAssunto = v ? `Titulos sem data de entrega - (${v})` : 'Titulos sem data de entrega';
      return;
    }

    // Financeiro / Cobrança: seleciona um único nome de cliente referente às notas
    const clientePrincipal = this.cards[0]?.fullClientName || this.cards[0]?.clientName || 'Cliente';
    this.composeAssunto = `Cobrança - Títulos Pendentes - ${clientePrincipal}`;
  }

  conectarGoogle(): void {
    this.googleAuthService.iniciarAutorizacaoPopup()
      .then(() => {
        this.mostrarAlerta('Conectado!', 'Sua conta do Gmail foi conectada com sucesso.', 'success');
      })
      .catch((err) => {
        const msg = typeof err === 'string' ? err : (err?.message || 'Falha ao conectar com o Google.');
        this.mostrarAlerta('Erro de Conexão', msg, 'danger');
      });
  }

  abrirConfirmarDesconexao(): void {
    this.confirmarDesconectarOpen = true;
  }

  desconectarGoogle(): void {
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

  private inserirAssinatura(): void {
    if (!this.composeBodyRef) return;
    const el = this.composeBodyRef.nativeElement;
    const htmlAtual = el.innerHTML.trim();

    const assinaturaJaPresente = htmlAtual.includes(this.ASSINATURA_URL);
    if (assinaturaJaPresente) return;

    const assinaturaHtml = `<br><br><img
      src="${this.ASSINATURA_URL}"
      alt="Assinatura"
      style="max-width: 580px; width: 100%; height: auto; display: block;"
      onerror="this.style.display='none'; document.dispatchEvent(new CustomEvent('assinatura-erro-lote'));"
    >`;

    if (!htmlAtual || htmlAtual === '<br>' || htmlAtual === '<div><br></div>') {
      el.innerHTML = assinaturaHtml;
    } else {
      el.innerHTML = htmlAtual + assinaturaHtml;
    }

    const handler = () => {
      this.assinaturaComErro = true;
      document.removeEventListener('assinatura-erro-lote', handler);
    };
    document.addEventListener('assinatura-erro-lote', handler, { once: true });
  }

  montarTabelaTitulosHtml(): string {
    const clientes = this.clientesDistintos;
    const exibirColunaCliente = clientes.length > 1;

    let tabelaHtml = `<table style="width: 100%; border-collapse: collapse; margin: 12px 0; font-family: sans-serif; font-size: 13px;">
      <thead>
        <tr style="background-color: #f3f4f6; border-bottom: 2px solid #e5e7eb; text-align: left;">
          <th style="padding: 8px 10px; font-weight: 600; color: #374151;">Título</th>
          <th style="padding: 8px 10px; font-weight: 600; color: #374151;">Parcela</th>
          ${exibirColunaCliente ? '<th style="padding: 8px 10px; font-weight: 600; color: #374151;">Cliente</th>' : ''}
          <th style="padding: 8px 10px; font-weight: 600; color: #374151;">Vencimento</th>
          <th style="padding: 8px 10px; font-weight: 600; color: #374151; text-align: right;">Saldo</th>
        </tr>
      </thead>
      <tbody>`;

    for (const card of this.cards) {
      const saldo = (card.valorSaldo || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      const venc = card.dtVencimento ? new Date(card.dtVencimento).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : '-';
      const parc = card.parccela || '-';

      tabelaHtml += `
        <tr style="border-bottom: 1px solid #e5e7eb;">
          <td style="padding: 8px 10px; font-weight: 500; color: #111827;">${card.title}</td>
          <td style="padding: 8px 10px; color: #4b5563;">${parc}</td>
          ${exibirColunaCliente ? `<td style="padding: 8px 10px; color: #4b5563;">${card.fullClientName || card.clientName}</td>` : ''}
          <td style="padding: 8px 10px; color: #4b5563;">${venc}</td>
          <td style="padding: 8px 10px; font-weight: 600; color: #b91c1c; text-align: right; font-variant-numeric: tabular-nums;">${saldo}</td>
        </tr>`;
    }

    const totalFormatado = this.valorTotalSaldo.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const colSpan = exibirColunaCliente ? 4 : 3;

    tabelaHtml += `
      <tr style="background-color: #f9fafb; font-weight: bold; border-top: 2px solid #d1d5db;">
        <td colspan="${colSpan}" style="padding: 10px; text-align: right; color: #111827;">Total Consolidado:</td>
        <td style="padding: 10px; text-align: right; color: #b91c1c; font-variant-numeric: tabular-nums;">${totalFormatado}</td>
      </tr>
      </tbody>
    </table>`;

    return tabelaHtml;
  }

  aplicarTemplate(tipo: 'cobranca' | 'recobranca' | 'protesto' | 'sem_data' | 'devolucao'): void {
    if (!this.composeBodyRef || this.cards.length === 0) return;

    this.sugerirAssunto(tipo);

    const el = this.composeBodyRef.nativeElement;
    const totalFormatado = this.valorTotalSaldo.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const assinaturaHtml = `<br><br><img src="${this.ASSINATURA_URL}" alt="Assinatura" style="max-width: 580px; width: 100%; height: auto; display: block;">`;
    const tabelaTitulos = this.montarTabelaTitulosHtml();
    const clientePrincipal = this.cards[0]?.fullClientName || this.cards[0]?.clientName || 'Cliente';
    const clienteRef = `<b>${clientePrincipal}</b>`;

    let textoHtml = '';

    switch (tipo) {
      case 'cobranca':
        textoHtml = `Prezado(a) ${clienteRef},<br><br>
Constam em nosso sistema os seguintes títulos pendentes de regularização, totalizando <b>${totalFormatado}</b>:<br>
${tabelaTitulos}
<br>
Caso os pagamentos já tenham sido efetuados, por favor, desconsidere esta mensagem e nos envie os comprovantes para que possamos realizar a baixa no sistema. Se houver algum contratempo ou se necessitar dos boletos atualizados, estamos à disposição para ajudar.<br><br>
Atenciosamente,${assinaturaHtml}`;
        break;
      case 'recobranca':
        textoHtml = `Prezado(a) ${clienteRef},<br><br>
Até o momento, não identificamos o pagamento referente aos títulos pendentes listados abaixo, totalizando <b>${totalFormatado}</b>:<br>
${tabelaTitulos}
<br>
Pedimos a gentileza de nos enviar os comprovantes caso a quitação já tenha ocorrido. Caso contrário, solicitamos uma previsão de pagamento para regularização das pendências ou que entre em contato conosco para verificarmos uma proposta de acordo.<br><br>
No aguardo de seu retorno,<br>Atenciosamente,${assinaturaHtml}`;
        break;
      case 'protesto':
        textoHtml = `Prezado(a) ${clienteRef},<br><br>
Informamos que os títulos abaixo discriminados, totalizando <b>${totalFormatado}</b>, continuam pendentes de pagamento em nosso sistema:<br>
${tabelaTitulos}
<br>
Como não obtivemos retorno nas notificações anteriores, comunicamos que, caso as pendências não sejam regularizadas (ou os respectivos comprovantes enviados) no prazo de <b>2 dias úteis</b>, os títulos serão encaminhados ao cartório competente para <b>protesto</b> e apontamento nos órgãos de proteção ao crédito.<br><br>
Para evitar transtornos e custos adicionais cartoriais, solicitamos a regularização imediata.<br><br>
Atenciosamente,${assinaturaHtml}`;
        break;
      case 'sem_data':
        textoHtml = `Prezados,<br><br>
Estamos realizando o acompanhamento das entregas de nossa carteira e verificamos que as notas/títulos abaixo relacionados (totalizando <b>${totalFormatado}</b>) ainda não possuem a confirmação da data exata de entrega registrada:<br>
${tabelaTitulos}
<br>
Poderiam, por gentileza, nos informar a posição e previsão de entrega dessas mercadorias?<br><br>
Agradecemos a atenção.<br>Atenciosamente,${assinaturaHtml}`;
        break;
      case 'devolucao':
        textoHtml = `Prezados,<br><br>
Identificamos em nosso sistema ocorrências de devolução envolvendo os seguintes títulos (totalizando <b>${totalFormatado}</b>):<br>
${tabelaTitulos}
<br>
Para que possamos realizar os devidos trâmites contábeis e financeiros, solicitamos que nos informem brevemente a posição referente a cada ocorrência.<br><br>
Permanecemos à disposição.<br>Atenciosamente,${assinaturaHtml}`;
        break;
    }

    el.innerHTML = textoHtml;
  }

  aplicarFormatacao(comando: string): void {
    document.execCommand(comando, false);
    if (this.composeBodyRef) {
      this.composeBodyRef.nativeElement.focus();
    }
  }

  triggerAnexo(): void {
    this.anexoInputRef?.nativeElement.click();
  }

  onAnexoSelecionado(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      for (let i = 0; i < input.files.length; i++) {
        this.arquivosSelecionados.push(input.files[i]);
      }
    }
    input.value = '';
  }

  removerArquivo(index: number): void {
    this.arquivosSelecionados.splice(index, 1);
  }

  formatarTamanhoArquivo(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  mostrarAlerta(titulo: string, mensagem: string, variant: 'primary' | 'danger' | 'success' = 'primary'): void {
    this.alertaTitulo = titulo;
    this.alertaMensagem = mensagem;
    this.alertaVariant = variant;
    this.alertaModalOpen = true;
  }

  enviarMensagem(): void {
    if (this.cards.length === 0 || this.isEnviandoEmail) return;

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

    if (!this.googleAuthService.isConectado()) {
      this.googleAuthService.iniciarAutorizacaoPopup()
        .then(() => this._dispararEnvio(corpo))
        .catch(() => this.mostrarAlerta('Autorização Necessária', 'É obrigatório conectar sua conta do Google antes de enviar e-mails.', 'danger'));
      return;
    }

    this._dispararEnvio(corpo);
  }

  private _dispararEnvio(corpo: string): void {
    if (this.cards.length === 0) return;

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

    const idsNf = this.cards.map(c => Number(c.id));

    this.importacoesService.enviarEmailLote(idsNf, formData).subscribe({
      next: (res) => {
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

        this.mostrarAlerta(
          'E-mail em Lote Enviado!',
          `A mensagem referente a ${res.total_titulos || idsNf.length} título(s) foi enviada com sucesso e registrada no histórico de cada um.`,
          'success'
        );

        this.enviado.emit();
        this.close();
      },
      error: (err) => {
        this.isEnviandoEmail = false;
        console.error('Erro ao enviar e-mail em lote:', err);
        const detalhe = err.error?.detail || err.message || 'Falha ao enviar e-mail em lote pelo Gmail.';
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
