import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import * as XLSX from 'xlsx';

import { FlatpickrModule } from 'angularx-flatpickr';
import { ButtonComponent } from '../../../shared/components/button/button.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { DespesasViagensService } from '../../../core/services/despesas-viagens.service';
import { EmpresasService } from '../../../core/services/empresas.service';
import { ColaboradoresService } from '../../../core/services/colaboradores.service';
import { CentrosCustoService } from '../../../core/services/centros-custo.service';
import { Portuguese } from 'flatpickr/dist/l10n/pt';

@Component({
  selector: 'app-relatorio-viagens',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, FlatpickrModule, ButtonComponent, ModalComponent, BadgeComponent],
  templateUrl: './relatorio-viagens.component.html',
  styleUrls: ['./relatorio-viagens.component.scss']
})
export class RelatorioViagensComponent implements OnInit {
  private despesasViagensService = inject(DespesasViagensService);
  private empresasService = inject(EmpresasService);
  private colaboradoresService = inject(ColaboradoresService);
  private centrosCustoService = inject(CentrosCustoService);

  locale = Portuguese;

  // Filtros Relatório
  relatorioDataInicio: Date | null = null;
  relatorioDataFim: Date | null = null;
  relatorioPeriodShortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-mes' | 'este-ano' | 'ano-passado' | 'personalizado' | null = 'este-ano';
  relatorioEmpresa: number | null = null;
  relatorioColaborador: number | null = null;


  isRelatorioLoading = false;
  relatorioDetalhesMatrizOriginal: any[] = [];
  relatorioDetalhesMatrizFiltrada: any[] = [];
  relatorioDetalhesCategoriasColunas: string[] = [];
  relatorioDetalhesTotaisPorCategoria: { [cat: string]: number } = {};
  relatorioDetalhesTotalGeral = 0;
  searchRelatorioTerm = '';

  // Modal de Conciliação
  isConciliacaoModalOpen = false;
  conciliacaoStep = signal<1 | 2 | 3>(1); // 1 = Upload, 2 = Loading, 3 = Resultado
  conciliacaoResult = signal<any | null>(null);
  conciliacaoFile = signal<File | null>(null);
  conciliacaoError = signal<string>('');
  activeConciliacaoTab = signal<'unidades' | 'empresas' | 'pessoas'>('unidades');
  searchConciliacaoTerm = signal<string>('');

  get filteredConciliacaoUnidades(): any[] {
    const res = this.conciliacaoResult();
    if (!res || !res.unidades) return [];
    const term = this.searchConciliacaoTerm().toLowerCase().trim();
    if (!term) return res.unidades;
    return res.unidades.filter((u: any) =>
      (u.unidade_descricao && u.unidade_descricao.toLowerCase().includes(term)) ||
      (u.unidade_codigo && u.unidade_codigo.toString().includes(term))
    );
  }

  get filteredConciliacaoEmpresas(): any[] {
    const res = this.conciliacaoResult();
    if (!res || !res.empresas) return [];
    const term = this.searchConciliacaoTerm().toLowerCase().trim();
    if (!term) return res.empresas;
    return res.empresas.filter((e: any) =>
      (e.empresa_nome && e.empresa_nome.toLowerCase().includes(term)) ||
      (e.empresa_abrev && e.empresa_abrev.toLowerCase().includes(term)) ||
      (e.unidade_codigo && e.unidade_codigo.toString().includes(term))
    );
  }

  get filteredConciliacaoPessoas(): any[] {
    const res = this.conciliacaoResult();
    if (!res || !res.pessoas) return [];
    const term = this.searchConciliacaoTerm().toLowerCase().trim();
    if (!term) return res.pessoas;
    return res.pessoas.filter((p: any) =>
      (p.colaborador_nome && p.colaborador_nome.toLowerCase().includes(term)) ||
      (p.nome_abrev && p.nome_abrev.toLowerCase().includes(term)) ||
      (p.unidade_codigo && p.unidade_codigo.toString().includes(term))
    );
  }

  // Listas para filtros
  listaEmpresasGeral: any[] = [];
  listaColaboradoresGeral: any[] = [];
  listaCentrosCusto: any[] = [];

  ngOnInit() {
    this.selecionarAtalhoPeriodoRelatorio('este-ano');
    this.carregarListasFiltro();
  }

  carregarListasFiltro() {
    this.empresasService.listar(1, 1000, '', 1).subscribe({
      next: (res: any) => this.listaEmpresasGeral = (res.items || []).sort((a: any, b: any) => (a.nome || '').localeCompare(b.nome || '')),
      error: (err: any) => console.error(err)
    });
    this.colaboradoresService.listar(1, 2000).subscribe({
      next: (res: any) => this.listaColaboradoresGeral = res.items || [],
      error: (err: any) => console.error(err)
    });
    this.centrosCustoService.listar(1, 1000).subscribe({
      next: (res: any) => this.listaCentrosCusto = res.items || [],
      error: (err: any) => console.error(err)
    });
  }

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
      (item.colaboradorNome && item.colaboradorNome.toLowerCase().includes(term)) ||
      (item.empresaNome && item.empresaNome.toLowerCase().includes(term)) ||
      (item.total && item.total.toString().includes(term))
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

  onRelatorioShortcutSelectChange(val: any) {
    if (val !== 'personalizado') {
      this.selecionarAtalhoPeriodoRelatorio(val);
    }
  }

  selecionarAtalhoPeriodoRelatorio(shortcut: 'ultimo-bimestre' | 'ultimo-semestre' | 'este-mes' | 'este-ano' | 'ano-passado') {
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
      case 'este-mes':
        this.relatorioDataInicio = new Date(today.getFullYear(), today.getMonth(), 1);
        this.relatorioDataFim = new Date(today.getFullYear(), today.getMonth() + 1, 0);
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
      id_colaborador: this.relatorioColaborador || null
    };

    this.despesasViagensService.obterRelatorio(filtros).subscribe({
      next: (dados) => {
        this.isRelatorioLoading = false;
        
        let matriz = dados.detalhesMatrizOriginal || [];
        
        this.relatorioDetalhesMatrizOriginal = matriz;
        this.relatorioDetalhesCategoriasColunas = dados.detalhesCategoriasColunas || [];
        this.relatorioDetalhesTotaisPorCategoria = dados.detalhesTotaisPorCategoria || {};
        this.relatorioDetalhesTotalGeral = dados.detalhesTotalGeral || 0;

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
      return;
    }

    const header = [
      'UNIDADE',
      'COLABORADOR',
      'EMPRESA',
      'CENTRO DE CUSTO',
      ...this.relatorioDetalhesCategoriasColunas,
      'TOTAL'
    ];

    const dataRows = this.relatorioDetalhesMatrizFiltrada.map(row => {
      const cc = row.centroCustoCodigo ? String(row.centroCustoCodigo).replace(/\.0$/, '') : '-';
      const r: any[] = [
        row.unidadeNome ? row.unidadeNome.split('-')[0].trim() : '-',
        row.colaboradorNome || '-',
        row.empresaNome || '-',
        cc
      ];
      this.relatorioDetalhesCategoriasColunas.forEach(cat => {
        r.push(row.valoresPorCategoria ? (row.valoresPorCategoria[cat] || 0) : 0);
      });
      r.push(row.total || 0);
      return r;
    });

    const footerRow: any[] = [
      'TOTAL GERAL',
      '',
      '',
      ''
    ];
    this.relatorioDetalhesCategoriasColunas.forEach(cat => {
      footerRow.push(this.relatorioDetalhesTotaisPorCategoria[cat] || 0);
    });
    footerRow.push(this.relatorioDetalhesTotalGeral || 0);

    const worksheet: XLSX.WorkSheet = XLSX.utils.aoa_to_sheet([header, ...dataRows, footerRow]);

    // Formatação contábil para valores numéricos apenas das categorias e total (colunas E em diante, índice >= 4)
    for (const cellKey of Object.keys(worksheet)) {
      if (cellKey.startsWith('!')) continue;
      const cellCoord = XLSX.utils.decode_cell(cellKey);
      if (cellCoord.r === 0) continue; // Pula linha de cabeçalho
      
      if (cellCoord.c >= 4) {
        const cell = worksheet[cellKey];
        if (cell && cell.t === 'n') {
          cell.z = '"R$" #,##0.00;("R$" #,##0.00);"-"';
        }
      }
    }

    // Auto-ajuste de largura das colunas para visualização ideal sem corte
    const allRows = [header, ...dataRows, footerRow];
    const colWidths = header.map((h, colIdx) => {
      let maxLen = h ? String(h).length : 10;
      for (const row of allRows) {
        const val = row[colIdx];
        if (val !== null && val !== undefined) {
          let strVal = '';
          if (typeof val === 'number') {
            strVal = val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            if (val !== 0 && colIdx >= 4) strVal = 'R$ ' + strVal;
          } else {
            strVal = String(val);
          }
          if (strVal.length > maxLen) {
            maxLen = strVal.length;
          }
        }
      }
      return { wch: Math.max(maxLen + 4, 14) };
    });
    worksheet['!cols'] = colWidths;

    // Altura destacada para a linha de cabeçalho
    worksheet['!rows'] = [
      { hpt: 26 }
    ];

    // Fixa o cabeçalho no topo da rolagem
    worksheet['!views'] = [{
      state: 'frozen',
      xSplit: 0,
      ySplit: 1
    }];

    const workbook: XLSX.WorkBook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Relatório Despesas');
    
    XLSX.writeFile(workbook, 'relatorio-despesas-viagens.xlsx');
  }

  abrirModalConciliacao() {
    this.conciliacaoStep.set(1);
    this.conciliacaoResult.set(null);
    this.conciliacaoFile.set(null);
    this.conciliacaoError.set('');
    this.activeConciliacaoTab.set('unidades');
    this.searchConciliacaoTerm.set('');
    this.isConciliacaoModalOpen = true;
  }

  fecharModalConciliacao() {
    this.isConciliacaoModalOpen = false;
  }

  onConciliacaoFileSelected(event: any) {
    const file = event.target?.files?.[0];
    if (file) {
      this.processarArquivoConciliacao(file);
    }
  }

  onConciliacaoFileDropped(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.processarArquivoConciliacao(event.dataTransfer.files[0]);
    }
  }

  onConciliacaoDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  processarArquivoConciliacao(file: File) {
    this.conciliacaoFile.set(file);
    this.conciliacaoError.set('');
    this.conciliacaoStep.set(2);

    this.despesasViagensService.conciliarPlanilha(file).subscribe({
      next: (res) => {
        this.conciliacaoResult.set(res);
        this.conciliacaoStep.set(3);
      },
      error: (err) => {
        console.error('Erro ao processar conciliação', err);
        this.conciliacaoError.set(err.error?.detail || 'Erro ao processar a planilha. Verifique o arquivo e tente novamente.');
        this.conciliacaoStep.set(1);
      }
    });
  }
}
