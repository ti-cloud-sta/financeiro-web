import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { PrevisaoCaixaService } from '../../core/services/previsao-caixa.service';
import { ToastService } from '../../core/services/toast.service';
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component';
import {
  ContaPagarItem,
  ContaReceberItem,
  HistoricoCliente,
  AtualizacaoHistoryItem,
  MatrizCardItem,
  MatrizReceberCardItem,
  BancoReceberCardItem
} from './previsao-caixa.mock';

@Component({
  selector: 'app-previsao-caixa',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonComponent, ModalComponent, ConfirmModalComponent, BadgeComponent, SkeletonComponent],
  templateUrl: './previsao-caixa.component.html',
  styleUrls: ['./previsao-caixa.component.scss']
})
export class PrevisaoCaixaComponent implements OnInit {
  private previsaoService = inject(PrevisaoCaixaService);
  private toastService = inject(ToastService);

  isSidebarCollapsed = false;
  activeSidebarTab = signal<'dashboards' | 'atualizacao-dados'>('dashboards');
  activeNav = signal<'visao-geral' | 'contas-pagar' | 'contas-receber'>('visao-geral');
  dataHoje = new Date().toLocaleDateString('pt-BR');
  dataReferenciaBackend = signal<string>('');
  isLoadingVisaoGeral = signal<boolean>(true);

  // Termos de busca
  pesquisaPagar = signal<string>('');
  pesquisaReceber = signal<string>('');

  // Toggle do modo provisão
  somenteProvisao = signal<boolean>(false);

  // Valor investido disponível para resgate
  valorInvestidoResgatavel = signal<number>(0);

  // Estado de Upload automático por card/input
  uploadStates = signal<Record<'pagar' | 'receber' | 'provisao' | 'investimento', {
    isProcessing: boolean;
    isSuccess: boolean;
    progress: number;
    message: string;
    fileName: string;
  }>>({
    pagar: { isProcessing: false, isSuccess: false, progress: 0, message: '', fileName: '' },
    receber: { isProcessing: false, isSuccess: false, progress: 0, message: '', fileName: '' },
    provisao: { isProcessing: false, isSuccess: false, progress: 0, message: '', fileName: '' },
    investimento: { isProcessing: false, isSuccess: false, progress: 0, message: '', fileName: '' }
  });

  // Histórico de Atualizações de Dados (filtrado para o tipo APB / Previsão de Caixa)
  atualizacoesHistory = signal<AtualizacaoHistoryItem[]>([]);
  isLoadingHistorico = signal<boolean>(false);
  searchAtualizacao = signal<string>('');

  filteredAtualizacoes = computed(() => {
    const term = this.searchAtualizacao().toLowerCase().trim();
    if (!term) return this.atualizacoesHistory();
    return this.atualizacoesHistory().filter(h =>
      h.nomeArquivo.toLowerCase().includes(term) ||
      h.tipo.toLowerCase().includes(term) ||
      h.autor.toLowerCase().includes(term) ||
      h.dataHora.includes(term)
    );
  });

  // Modal de Exclusão de Histórico
  isConfirmDeleteOpen = signal<boolean>(false);
  itemDeleteId = signal<string | null>(null);
  itemDeleteIdImportacoes = signal<number | null>(null);

  // Contas reais carregadas do backend
  contasPagar = signal<ContaPagarItem[]>([]);
  contasReceber = signal<ContaReceberItem[]>([]);

  // Estado do Modal de Histórico do Cliente
  isHistoricoModalOpen = signal<boolean>(false);
  clienteSelecionado = signal<HistoricoCliente | null>(null);

  // Estado do Modal de Detalhes de Pagamento
  isDetalhePagarModalOpen = signal<boolean>(false);
  pagarSelecionado = signal<ContaPagarItem | null>(null);

  // Estado do Modal de Títulos Agrupados por Matriz
  isMatrizModalOpen = signal<boolean>(false);
  matrizSelecionada = signal<MatrizCardItem | null>(null);

  // Estado do Modal de Ação de Receber (Simular Recebimento)
  isAcaoReceberModalOpen = signal<boolean>(false);
  receberSelecionado = signal<ContaReceberItem | null>(null);

  // Matrizes de Receber agrupadas por Matriz e Modalidade
  matrizesReceber = signal<MatrizReceberCardItem[]>([]);
  matrizReceberSelecionada = signal<MatrizReceberCardItem | null>(null);
  isMatrizReceberModalOpen = signal<boolean>(false);

  // Estado do Modal de Títulos do Banco a Receber
  bancoReceberSelecionado = signal<BancoReceberCardItem | null>(null);
  isBancoModalOpen = signal<boolean>(false);

  // Filtro por Pílulas de Score no Header do Receber ou Clique nos KPI Cards (TODOS, ALTO, MEDIO, BAIXO, NOVOS, MENOR_IGUAL_90, MAIOR_90)
  filtroScore = signal<'TODOS' | 'ALTO' | 'MEDIO' | 'BAIXO' | 'NOVOS' | 'MENOR_IGUAL_80' | 'MAIOR_80' | 'MENOR_IGUAL_90' | 'MAIOR_90'>('TODOS');

  ngOnInit() {
    this.isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    this.carregarHistoricoImportacoes();
    this.carregarVisaoGeral();
  }

  carregarVisaoGeral(data?: string) {
    this.isLoadingVisaoGeral.set(true);
    this.previsaoService.obterVisaoGeral(data).subscribe({
      next: (res) => {
        this.isLoadingVisaoGeral.set(false);
        this.dataHoje = res.data_formatada || new Date().toLocaleDateString('pt-BR');
        this.dataReferenciaBackend.set(res.data_referencia);
        this.valorInvestidoResgatavel.set(res.valor_investido_resgatavel || 0);

        const todasContasPagar: ContaPagarItem[] = [
          ...(res.contas_bb || []),
          ...(res.contas_itau || []),
          ...(res.contas_provisao || [])
        ];
        this.contasPagar.set(todasContasPagar);
        this.contasReceber.set(res.contas_receber || []);
        this.matrizesReceber.set(res.matrizes_receber || []);
      },
      error: (err) => {
        this.isLoadingVisaoGeral.set(false);
        const msg = err.error?.detail || err.message || 'Erro ao carregar dados da Visão Geral.';
        this.toastService.show(msg, 'error');
      }
    });
  }

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  setActiveNav(nav: 'visao-geral' | 'contas-pagar' | 'contas-receber') {
    this.activeNav.set(nav);
  }

  toggleSomenteProvisao() {
    this.somenteProvisao.update(v => !v);
  }

  // ==========================================
  // CÁLCULOS DOS CARDS SUPERIORES (DASHBOARD)
  // ==========================================

  // Card 1: Total em Provisão
  totalProvisao = computed(() => {
    return this.contasPagar()
      .filter(item => item.tipo === 'PROVISAO')
      .reduce((acc, curr) => acc + curr.valor, 0);
  });

  qtdProvisoes = computed(() => {
    return this.contasPagar().filter(item => item.tipo === 'PROVISAO').length;
  });

  // Card 2: Total a Pagar (apenas contas reais BB + Itaú)
  totalPagar = computed(() => {
    return this.contasPagar()
      .filter(item => item.tipo === 'REAL')
      .reduce((acc, curr) => acc + curr.valor, 0);
  });

  qtdPagarReal = computed(() => {
    return this.contasPagar().filter(item => item.tipo === 'REAL').length;
  });

  // Card 3: Total a Receber (todas as contas a receber reais)
  totalReceber = computed(() => {
    return this.contasReceber().reduce((acc, curr) => acc + curr.valor, 0);
  });

  qtdReceber = computed(() => {
    return this.contasReceber().length;
  });

  // Card 4: Previsão < 90% chance de receber
  receberMenorIgual90 = computed(() => {
    return this.contasReceber()
      .filter(item => item.score < 90)
      .reduce((acc, curr) => acc + curr.valor, 0);
  });
  receberMenorIgual80 = this.receberMenorIgual90;

  qtdReceberMenorIgual90 = computed(() => {
    return this.contasReceber().filter(item => item.score < 90).length;
  });
  qtdReceberMenorIgual80 = this.qtdReceberMenorIgual90;

  // Card 5: Previsão >= 90% chance de receber (Previsto / Bom)
  receberMaior90 = computed(() => {
    return this.contasReceber()
      .filter(item => item.score >= 90)
      .reduce((acc, curr) => acc + curr.valor, 0);
  });
  receberMaior80 = this.receberMaior90;

  qtdReceberMaior90 = computed(() => {
    return this.contasReceber().filter(item => item.score >= 90).length;
  });
  qtdReceberMaior80 = this.qtdReceberMaior90;

  // Card 6: Previsão de Saldo (Sobrar ou Faltar)
  // Previsibilidade ponderada pelo score dos clientes: sum(valor * score%)
  totalReceberPonderado = computed(() => {
    return this.contasReceber().reduce((acc, curr) => {
      const probabilidade = Math.max(0, Math.min(100, curr.score)) / 100;
      return acc + (curr.valor * probabilidade);
    }, 0);
  });

  // Saldo ajustado pela previsibilidade dos scores: (Receber Ponderado - Pagar)
  saldoPrevisibilidade = computed(() => {
    return this.totalReceberPonderado() - this.totalPagar();
  });

  // Saldo Real / Nominal (Receber Nominal - Pagar Nominal, sem verificar score)
  saldoRealNominal = computed(() => {
    return this.totalReceber() - this.totalPagar();
  });

  isSaldoPrevisibilidadePositivo = computed(() => {
    return this.saldoPrevisibilidade() >= 0;
  });

  isSaldoRealPositivo = computed(() => {
    return this.saldoRealNominal() >= 0;
  });

  // ==========================================
  // LISTAS FILTRADAS POR COLUNA E BUSCA
  // ==========================================

  // Filtro Contas a Pagar
  contasPagarFiltradas = computed(() => {
    const termo = this.pesquisaPagar().toLowerCase().trim();
    if (!termo) return this.contasPagar();
    return this.contasPagar().filter(item =>
      item.favorecido.toLowerCase().includes(termo) ||
      item.categoria.toLowerCase().includes(termo) ||
      item.descricao.toLowerCase().includes(termo) ||
      (item.numeroDocumento && item.numeroDocumento.toLowerCase().includes(termo)) ||
      (item.nomeMatriz && item.nomeMatriz.toLowerCase().includes(termo)) ||
      (item.codigoMatriz && item.codigoMatriz.toLowerCase().includes(termo)) ||
      (item.clienteNome && item.clienteNome.toLowerCase().includes(termo))
    );
  });

  contasBB = computed(() => {
    return this.contasPagarFiltradas().filter(
      item => item.banco === 'BANCO_DO_BRASIL' && item.tipo === 'REAL'
    );
  });

  totalBB = computed(() => {
    return this.contasBB().reduce((acc, curr) => acc + curr.valor, 0);
  });

  contasItau = computed(() => {
    return this.contasPagarFiltradas().filter(
      item => item.banco === 'ITAU' && item.tipo === 'REAL'
    );
  });

  totalItau = computed(() => {
    return this.contasItau().reduce((acc, curr) => acc + curr.valor, 0);
  });

  contasProvisao = computed(() => {
    return this.contasPagarFiltradas().filter(item => item.tipo === 'PROVISAO');
  });

  totalContasProvisao = computed(() => {
    return this.contasProvisao().reduce((acc, curr) => acc + curr.valor, 0);
  });

  // ==========================================
  // AGRUPAMENTO DE CARDS POR MATRIZ
  // ==========================================
  agruparContasPorMatriz(itens: ContaPagarItem[]): MatrizCardItem[] {
    const mapa = new Map<string, MatrizCardItem>();

    for (const item of itens) {
      const key = item.idMatriz ? `id_${item.idMatriz}` : (item.codigoMatriz ? `cod_${item.codigoMatriz}` : `nome_${item.favorecido}`);
      const nomeMatriz = item.nomeMatriz || item.favorecido;
      const codigoMatriz = item.codigoMatriz || item.categoria || '';

      if (!mapa.has(key)) {
        mapa.set(key, {
          idMatriz: item.idMatriz,
          codigoMatriz: codigoMatriz,
          nomeMatriz: nomeMatriz,
          banco: item.banco,
          tipo: item.tipo,
          valorTotal: 0,
          qtdTitulos: 0,
          titulos: []
        });
      }

      const grupo = mapa.get(key)!;
      grupo.valorTotal += item.valor;
      grupo.qtdTitulos += 1;
      grupo.titulos.push({
        id: Number(item.id),
        numeroDocumento: item.numeroDocumento,
        valor: item.valor,
        clienteCodigo: item.clienteCodigo,
        clienteNome: item.clienteNome || item.favorecido,
        dataVencimento: item.dataVencimento,
        banco: item.banco,
        categoria: item.categoria,
        descricao: item.descricao
      });
    }

    return Array.from(mapa.values())
      .map(g => ({
        ...g,
        valorTotal: Math.round((g.valorTotal + Number.EPSILON) * 100) / 100
      }))
      .sort((a, b) => b.valorTotal - a.valorTotal);
  }

  matrizesBB = computed(() => {
    return this.agruparContasPorMatriz(this.contasBB());
  });

  matrizesItau = computed(() => {
    return this.agruparContasPorMatriz(this.contasItau());
  });

  matrizesProvisao = computed(() => {
    return this.agruparContasPorMatriz(this.contasProvisao());
  });

  abrirModalMatriz(matriz: MatrizCardItem) {
    this.matrizSelecionada.set(matriz);
    this.isMatrizModalOpen.set(true);
  }

  fecharModalMatriz() {
    this.isMatrizModalOpen.set(false);
    this.matrizSelecionada.set(null);
  }

  // Filtro Contas a Receber (Itens Individuais para contadores e KPIs)
  contasReceberFiltradas = computed(() => {
    const termo = this.pesquisaReceber().toLowerCase().trim();
    if (!termo) return this.contasReceber();
    return this.contasReceber().filter(item =>
      item.clienteNome.toLowerCase().includes(termo) ||
      item.clienteCodigo.toLowerCase().includes(termo) ||
      item.documento.toLowerCase().includes(termo)
    );
  });

  contasCarteira = computed(() => {
    return this.contasReceberFiltradas().filter(item => item.modalidade === 'CARTEIRA');
  });

  contasBoleto = computed(() => {
    return this.contasReceberFiltradas().filter(item => item.modalidade === 'BOLETO');
  });

  // Filtro Matrizes a Receber (Cards Agrupados por Matriz, Pílula de Score e Busca Textual)
  matrizesReceberFiltradas = computed(() => {
    let lista = this.matrizesReceber();

    // 1. Filtro por Pílula de Score
    const fScore = this.filtroScore();
    if (fScore === 'ALTO') {
      lista = lista.filter(m => m.score >= 90);
    } else if (fScore === 'MEDIO') {
      lista = lista.filter(m => m.score >= 60 && m.score < 90);
    } else if (fScore === 'BAIXO') {
      lista = lista.filter(m => m.score < 60);
    } else if (fScore === 'NOVOS') {
      lista = lista.filter(m => m.isNovo || m.score === 0 || (m.titulosEmDia + m.titulosEmAtraso === 0));
    } else if (fScore === 'MENOR_IGUAL_90' || fScore === 'MENOR_IGUAL_80') {
      lista = lista.filter(m => m.score < 90);
    } else if (fScore === 'MAIOR_90' || fScore === 'MAIOR_80') {
      lista = lista.filter(m => m.score >= 90);
    }

    // 2. Filtro de Busca Textual
    const termo = this.pesquisaReceber().toLowerCase().trim();
    if (!termo) return lista;

    return lista.filter(m =>
      (m.nomeMatriz && m.nomeMatriz.toLowerCase().includes(termo)) ||
      (m.codigoMatriz && m.codigoMatriz.toLowerCase().includes(termo)) ||
      (m.titulos && m.titulos.some(t =>
        (t.numeroDocumento && String(t.numeroDocumento).toLowerCase().includes(termo)) ||
        (t.clienteNome && t.clienteNome.toLowerCase().includes(termo)) ||
        (t.clienteCodigo && String(t.clienteCodigo).toLowerCase().includes(termo))
      ))
    );
  });

  // Quantidade total de títulos a receber filtrados
  totalTitulosReceberFiltrados = computed(() => {
    return this.matrizesReceberFiltradas().reduce((acc, curr) => acc + curr.qtdTitulos, 0);
  });

  setFiltroScore(tipo: 'TODOS' | 'ALTO' | 'MEDIO' | 'BAIXO' | 'NOVOS' | 'MENOR_IGUAL_80' | 'MAIOR_80' | 'MENOR_IGUAL_90' | 'MAIOR_90') {
    if (this.filtroScore() === tipo) {
      this.filtroScore.set('TODOS');
    } else {
      this.filtroScore.set(tipo);
    }
  }

  filtrarMenorIgual90() {
    if (this.filtroScore() === 'MENOR_IGUAL_90') {
      this.filtroScore.set('TODOS');
    } else {
      this.filtroScore.set('MENOR_IGUAL_90');
    }
  }

  filtrarMaior90() {
    if (this.filtroScore() === 'MAIOR_90') {
      this.filtroScore.set('TODOS');
    } else {
      this.filtroScore.set('MAIOR_90');
    }
  }

  filtrarMenorIgual80() {
    this.filtrarMenorIgual90();
  }

  filtrarMaior80() {
    this.filtrarMaior90();
  }

  filtrarENavegar(tipo: 'MENOR_IGUAL_80' | 'MAIOR_80' | 'MENOR_IGUAL_90' | 'MAIOR_90', event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.filtroScore.set(tipo);
    this.activeNav.set('contas-receber');
  }

  limparFiltroScore() {
    this.filtroScore.set('TODOS');
  }

  // Proporções para as barras de progresso da Visão Geral
  porcentagemBB = computed(() => {
    const total = this.totalPagar();
    return total > 0 ? (this.totalBB() / total) * 100 : 0;
  });

  porcentagemItau = computed(() => {
    const total = this.totalPagar();
    return total > 0 ? (this.totalItau() / total) * 100 : 0;
  });

  porcentagemCoberturaReceber = computed(() => {
    const pagar = this.totalPagar();
    if (pagar <= 0) return this.totalReceber() > 0 ? 100 : 0;
    return Math.min(100, (this.totalReceber() / pagar) * 100);
  });

  porcentagemCarteira = computed(() => {
    const total = this.totalReceber();
    return total > 0 ? (this.totalCarteira() / total) * 100 : 0;
  });

  porcentagemBoleto = computed(() => {
    const total = this.totalReceber();
    return total > 0 ? (this.totalBoleto() / total) * 100 : 0;
  });

  porcentagemMenor90 = computed(() => {
    const total = this.receberMenorIgual90() + this.receberMaior90();
    return total > 0 ? (this.receberMenorIgual90() / total) * 100 : 0;
  });
  porcentagemMenor80 = this.porcentagemMenor90;

  porcentagemMaior90 = computed(() => {
    const total = this.receberMenorIgual90() + this.receberMaior90();
    return total > 0 ? (this.receberMaior90() / total) * 100 : 0;
  });
  porcentagemMaior80 = this.porcentagemMaior90;

  matrizesCarteira = computed(() => {
    return this.matrizesReceberFiltradas().filter(item => item.modalidade === 'CARTEIRA');
  });

  totalCarteira = computed(() => {
    return this.matrizesCarteira().reduce((acc, curr) => acc + curr.valorTotal, 0);
  });

  matrizesBoleto = computed(() => {
    return this.matrizesReceberFiltradas().filter(item => item.modalidade === 'BOLETO');
  });

  totalBoleto = computed(() => {
    return this.matrizesBoleto().reduce((acc, curr) => acc + curr.valorTotal, 0);
  });

  // ==========================================
  // AGRUPAMENTO DE CONTAS A RECEBER POR BANCO
  // ==========================================
  bancosReceber = computed<BancoReceberCardItem[]>(() => {
    const matrizes = this.matrizesReceberFiltradas();

    const bancosConfig: Record<string, { nome: string; logo: string; logoImg?: string; cor: string; ordem: number }> = {
      'ITAU': { nome: 'Itaú', logo: 'IT', logoImg: 'images/logos/itau.png', cor: '#f97316', ordem: 1 },
      'BANCO_DO_BRASIL': { nome: 'Banco do Brasil', logo: 'BB', logoImg: 'images/logos/bb.png', cor: '#eab308', ordem: 2 },
      'SANTANDER': { nome: 'Santander', logo: 'SAN', logoImg: 'images/logos/santander.png', cor: '#dc2626', ordem: 3 },
      'BRADESCO': { nome: 'Bradesco', logo: 'BRA', logoImg: 'images/logos/bradesco.png', cor: '#cc092f', ordem: 4 },
      'CARTEIRA': { nome: 'Carteira', logo: 'CRT', cor: '#0891b2', ordem: 5 },
      'DAYCOVAL': { nome: 'Daycoval', logo: 'DAY', cor: '#1e3a8a', ordem: 6 }
    };

    const mapa = new Map<string, BancoReceberCardItem>();

    // Inicializa sempre os 4 bancos principais citados na especificação
    const bancosPrincipais = ['ITAU', 'BANCO_DO_BRASIL', 'SANTANDER', 'BRADESCO'];
    for (const cod of bancosPrincipais) {
      const cfg = bancosConfig[cod];
      mapa.set(cod, {
        codigo: cod,
        nome: cfg.nome,
        logo: cfg.logo,
        logoImg: cfg.logoImg,
        cor: cfg.cor,
        valorTotal: 0,
        qtdTitulos: 0,
        valorCarteira: 0,
        qtdCarteira: 0,
        valorBoleto: 0,
        qtdBoleto: 0,
        valorMaior90: 0,
        qtdMaior90: 0,
        matrizes: [],
        matrizesCarteira: [],
        matrizesBoleto: []
      });
    }

    for (const m of matrizes) {
      let bCod = m.bancoCodigo || '';
      if (!bCod) {
        const portStr = String(m.port || '').trim();
        if (portStr.endsWith('341') || portStr === '50341' || portStr === '10341') bCod = 'ITAU';
        else if (portStr.endsWith('001') || portStr === '50001' || portStr === '10001') bCod = 'BANCO_DO_BRASIL';
        else if (portStr.endsWith('033') || portStr === '50033' || portStr === '10033') bCod = 'SANTANDER';
        else if (portStr.endsWith('237') || portStr === '50237' || portStr === '10237') bCod = 'BRADESCO';
        else if (portStr.endsWith('707') || portStr === '10707') bCod = 'DAYCOVAL';
        else if (m.modalidade === 'CARTEIRA' || portStr === '95000' || portStr === '95100' || portStr === '95080') bCod = 'CARTEIRA';
        else bCod = portStr ? `OUTRO_${portStr}` : 'OUTROS';
      }

      if (!mapa.has(bCod)) {
        const cfg = bancosConfig[bCod] || {
          nome: m.bancoNome || bCod,
          logo: m.bancoLogo || 'BC',
          logoImg: m.bancoLogoImg,
          cor: m.bancoCor || '#64748b',
          ordem: 99
        };
        mapa.set(bCod, {
          codigo: bCod,
          nome: cfg.nome,
          logo: cfg.logo,
          logoImg: cfg.logoImg || m.bancoLogoImg,
          cor: cfg.cor,
          valorTotal: 0,
          qtdTitulos: 0,
          valorCarteira: 0,
          qtdCarteira: 0,
          valorBoleto: 0,
          qtdBoleto: 0,
          valorMaior90: 0,
          qtdMaior90: 0,
          matrizes: [],
          matrizesCarteira: [],
          matrizesBoleto: []
        });
      }

      const banco = mapa.get(bCod)!;
      banco.valorTotal = Math.round((banco.valorTotal + m.valorTotal + Number.EPSILON) * 100) / 100;
      banco.qtdTitulos += m.qtdTitulos;
      banco.matrizes.push(m);

      if (Number(m.score) >= 90) {
        banco.valorMaior90 = Math.round((banco.valorMaior90 + m.valorTotal + Number.EPSILON) * 100) / 100;
        banco.qtdMaior90 += m.qtdTitulos;
      }

      if (m.modalidade === 'CARTEIRA') {
        banco.valorCarteira = Math.round((banco.valorCarteira + m.valorTotal + Number.EPSILON) * 100) / 100;
        banco.qtdCarteira += m.qtdTitulos;
        banco.matrizesCarteira.push(m);
      } else {
        banco.valorBoleto = Math.round((banco.valorBoleto + m.valorTotal + Number.EPSILON) * 100) / 100;
        banco.qtdBoleto += m.qtdTitulos;
        banco.matrizesBoleto.push(m);
      }
    }

    const lista = Array.from(mapa.values());
    return lista.sort((a, b) => {
      const ordemA = bancosConfig[a.codigo]?.ordem ?? 99;
      const ordemB = bancosConfig[b.codigo]?.ordem ?? 99;
      if (ordemA !== ordemB) return ordemA - ordemB;
      return b.valorTotal - a.valorTotal;
    });
  });

  bancoModalAtual = computed(() => {
    const sel = this.bancoReceberSelecionado();
    if (!sel) return null;
    const atual = this.bancosReceber().find(b => b.codigo === sel.codigo);
    return atual || sel;
  });

  abrirModalBanco(banco: BancoReceberCardItem) {
    this.bancoReceberSelecionado.set(banco);
    this.isBancoModalOpen.set(true);
  }

  fecharModalBanco() {
    this.isBancoModalOpen.set(false);
    this.bancoReceberSelecionado.set(null);
  }

  getBancoLogoImg(codigo: string | undefined): string | null {
    if (!codigo) return null;
    const c = codigo.toUpperCase();
    if (c === 'ITAU' || c === '50341' || c === '10341' || c.endsWith('341')) return 'images/logos/itau.png';
    if (c === 'BANCO_DO_BRASIL' || c === 'BB' || c === '50001' || c === '10001' || c.endsWith('001')) return 'images/logos/bb.png';
    if (c === 'SANTANDER' || c === 'SAN' || c === '50033' || c === '10033' || c.endsWith('033')) return 'images/logos/santander.png';
    if (c === 'BRADESCO' || c === 'BRA' || c === '50237' || c === '10237' || c.endsWith('237')) return 'images/logos/bradesco.png';
    return null;
  }

  // ==========================================
  // INTERAÇÕES E MODAIS
  // ==========================================

  abrirHistoricoCliente(item: ContaReceberItem) {
    this.clienteSelecionado.set(item.historico);
    this.isHistoricoModalOpen.set(true);
  }

  fecharHistoricoModal() {
    this.isHistoricoModalOpen.set(false);
    this.clienteSelecionado.set(null);
  }

  abrirDetalhesPagar(item: ContaPagarItem) {
    this.pagarSelecionado.set(item);
    this.isDetalhePagarModalOpen.set(true);
  }

  fecharDetalhesPagarModal() {
    this.isDetalhePagarModalOpen.set(false);
    this.pagarSelecionado.set(null);
  }

  abrirAcaoReceber(item: ContaReceberItem) {
    this.receberSelecionado.set(item);
    this.isAcaoReceberModalOpen.set(true);
  }

  fecharAcaoReceberModal() {
    this.isAcaoReceberModalOpen.set(false);
    this.receberSelecionado.set(null);
  }

  abrirModalMatrizReceber(matriz: MatrizReceberCardItem) {
    this.matrizReceberSelecionada.set(matriz);
    this.isMatrizReceberModalOpen.set(true);
  }

  fecharModalMatrizReceber() {
    this.isMatrizReceberModalOpen.set(false);
    this.matrizReceberSelecionada.set(null);
  }

  // ==========================================
  // FORMATADORES AUXILIARES
  // ==========================================

  formatarMoeda(valor: number): string {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  getScoreBadgeClass(score: number): string {
    if (score >= 90) return 'score-high';
    if (score >= 60) return 'score-medium';
    return 'score-low';
  }

  getScoreVariant(score: number): 'success' | 'warning' | 'danger' {
    if (score >= 90) return 'success';
    if (score >= 60) return 'warning';
    return 'danger';
  }

  // ==========================================
  // MÉTODOS DE ATUALIZAÇÃO DE DADOS (4 UPLOADS)
  // ==========================================

  carregarHistoricoImportacoes() {
    this.isLoadingHistorico.set(true);
    // Lista as importações dos tipos pertinentes a Previsão de Caixa (APB, ACR, etc.)
    this.previsaoService.listarImportacoes().subscribe({
      next: (dados) => {
        this.atualizacoesHistory.set(dados);
        this.isLoadingHistorico.set(false);
      },
      error: (err) => {
        this.isLoadingHistorico.set(false);
        console.warn('Erro ao carregar histórico de importações do backend:', err);
      }
    });
  }

  onFileSelected(tipo: 'pagar' | 'receber' | 'provisao' | 'investimento', event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const fileName = file.name;

    if (tipo === 'pagar') {
      // 1. Upload REAL no backend para a tabela previsao_apb
      this.uploadStates.update(states => ({
        ...states,
        pagar: {
          isProcessing: true,
          isSuccess: false,
          progress: 20,
          message: 'Lendo e validando layout da planilha...',
          fileName
        }
      }));

      const progressTimer = setInterval(() => {
        this.uploadStates.update(states => {
          if (!states.pagar.isProcessing) return states;
          const novoProgresso = Math.min(85, states.pagar.progress + 15);
          return {
            ...states,
            pagar: {
              ...states.pagar,
              progress: novoProgresso,
              message: novoProgresso >= 60 ? 'Gravando registros no banco de dados...' : 'Processando linhas da aba DADOS...'
            }
          };
        });
      }, 300);

      this.previsaoService.importarApb(file).subscribe({
        next: (res) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            pagar: {
              isProcessing: false,
              isSuccess: true,
              progress: 100,
              message: 'Processado com sucesso!',
              fileName
            }
          }));
          this.toastService.show(res.mensagem || 'Arquivo APB importado com sucesso!', 'success');
          this.carregarHistoricoImportacoes();
          this.carregarVisaoGeral();
          input.value = '';
        },
        error: (err) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            pagar: {
              isProcessing: false,
              isSuccess: false,
              progress: 0,
              message: '',
              fileName: ''
            }
          }));
          const msg = err.error?.detail || err.message || 'Erro ao importar arquivo APB.';
          this.toastService.show(msg, 'error');
          input.value = '';
        }
      });
      return;
    }

    if (tipo === 'receber') {
      // 2. Upload REAL no backend para a tabela previsao_acr
      this.uploadStates.update(states => ({
        ...states,
        receber: {
          isProcessing: true,
          isSuccess: false,
          progress: 20,
          message: 'Lendo e validando layout da planilha...',
          fileName
        }
      }));

      const progressTimer = setInterval(() => {
        this.uploadStates.update(states => {
          if (!states.receber.isProcessing) return states;
          const novoProgresso = Math.min(85, states.receber.progress + 15);
          return {
            ...states,
            receber: {
              ...states.receber,
              progress: novoProgresso,
              message: novoProgresso >= 60 ? 'Gravando registros no banco de dados...' : 'Processando títulos a receber da planilha ACR...'
            }
          };
        });
      }, 300);

      this.previsaoService.importarAcr(file).subscribe({
        next: (res) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            receber: {
              isProcessing: false,
              isSuccess: true,
              progress: 100,
              message: 'Processado com sucesso!',
              fileName
            }
          }));
          this.toastService.show(res.mensagem || 'Arquivo ACR importado com sucesso!', 'success');
          this.carregarHistoricoImportacoes();
          this.carregarVisaoGeral();
          input.value = '';
        },
        error: (err) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            receber: {
              isProcessing: false,
              isSuccess: false,
              progress: 0,
              message: '',
              fileName: ''
            }
          }));
          const msg = err.error?.detail || err.message || 'Erro ao importar arquivo ACR.';
          this.toastService.show(msg, 'error');
          input.value = '';
        }
      });
      return;
    }

    if (tipo === 'provisao') {
      // 3. Upload REAL no backend para a tabela previsao_titulos_liquidados
      this.uploadStates.update(states => ({
        ...states,
        provisao: {
          isProcessing: true,
          isSuccess: false,
          progress: 15,
          message: 'Lendo planilha de títulos liquidados...',
          fileName
        }
      }));

      const progressTimer = setInterval(() => {
        this.uploadStates.update(states => {
          if (!states.provisao.isProcessing) return states;
          const novoProgresso = Math.min(85, states.provisao.progress + 10);
          return {
            ...states,
            provisao: {
              ...states.provisao,
              progress: novoProgresso,
              message: novoProgresso >= 60 ? 'Gravando lotes no banco de dados...' : 'Processando títulos liquidados...'
            }
          };
        });
      }, 400);

      this.previsaoService.importarTitulosLiquidados(file).subscribe({
        next: (res) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            provisao: {
              isProcessing: false,
              isSuccess: true,
              progress: 100,
              message: 'Processado com sucesso!',
              fileName
            }
          }));
          this.toastService.show(res.mensagem || 'Títulos Liquidados importados com sucesso!', 'success');
          this.carregarHistoricoImportacoes();
          this.carregarVisaoGeral();
          input.value = '';
        },
        error: (err) => {
          clearInterval(progressTimer);
          this.uploadStates.update(states => ({
            ...states,
            provisao: {
              isProcessing: false,
              isSuccess: false,
              progress: 0,
              message: '',
              fileName: ''
            }
          }));
          const msg = err.error?.detail || err.message || 'Erro ao importar títulos liquidados.';
          this.toastService.show(msg, 'error');
          input.value = '';
        }
      });
      return;
    }

    // Para o input 4 (investimento - mock até criação de seu endpoint)
    this.uploadStates.update(states => ({
      ...states,
      [tipo]: {
        isProcessing: true,
        isSuccess: false,
        progress: 25,
        message: 'Lendo e validando layout...',
        fileName
      }
    }));

    setTimeout(() => {
      this.uploadStates.update(states => ({
        ...states,
        [tipo]: {
          ...states[tipo],
          progress: 60,
          message: 'Processando registros...'
        }
      }));
    }, 400);

    setTimeout(() => {
      this.uploadStates.update(states => ({
        ...states,
        [tipo]: {
          ...states[tipo],
          progress: 90,
          message: 'Gravando atualizações...'
        }
      }));
    }, 800);

    setTimeout(() => {
      this.uploadStates.update(states => ({
        ...states,
        [tipo]: {
          isProcessing: false,
          isSuccess: true,
          progress: 100,
          message: 'Processado com sucesso!',
          fileName
        }
      }));
      input.value = '';
    }, 1200);
  }

  resetUpload(tipo: 'pagar' | 'receber' | 'provisao' | 'investimento', event: MouseEvent) {
    event.stopPropagation();
    this.uploadStates.update(states => ({
      ...states,
      [tipo]: { isProcessing: false, isSuccess: false, progress: 0, message: '', fileName: '' }
    }));
  }

  solicitarExclusaoAtualizacao(item: AtualizacaoHistoryItem | string) {
    if (typeof item === 'string') {
      this.itemDeleteId.set(item);
      const achado = this.atualizacoesHistory().find(h => h.id === item);
      this.itemDeleteIdImportacoes.set(achado?.idImportacoes || null);
    } else {
      this.itemDeleteId.set(item.id);
      this.itemDeleteIdImportacoes.set(item.idImportacoes || null);
    }
    this.isConfirmDeleteOpen.set(true);
  }

  confirmarExclusaoAtualizacao() {
    const idImp = this.itemDeleteIdImportacoes();
    const strId = this.itemDeleteId();

    if (idImp) {
      this.previsaoService.excluirImportacao(idImp).subscribe({
        next: (res) => {
          this.toastService.show(res.mensagem || 'Importação excluída com sucesso!', 'success');
          this.carregarHistoricoImportacoes();
          this.fecharConfirmDelete();
        },
        error: (err) => {
          const msg = err.error?.detail || 'Erro ao excluir importação.';
          this.toastService.show(msg, 'error');
          this.fecharConfirmDelete();
        }
      });
    } else if (strId) {
      this.atualizacoesHistory.update(hist => hist.filter(item => item.id !== strId));
      this.fecharConfirmDelete();
    }
  }

  fecharConfirmDelete() {
    this.isConfirmDeleteOpen.set(false);
    this.itemDeleteId.set(null);
    this.itemDeleteIdImportacoes.set(null);
  }
}


