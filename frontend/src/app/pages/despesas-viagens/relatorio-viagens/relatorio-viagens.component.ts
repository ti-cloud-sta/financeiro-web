import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import * as XLSX from 'xlsx';

import { FlatpickrModule } from 'angularx-flatpickr';
import { DespesasViagensService } from '../../../core/services/despesas-viagens.service';
import { EmpresasService } from '../../../core/services/empresas.service';
import { ColaboradoresService } from '../../../core/services/colaboradores.service';
import { CentrosCustoService } from '../../../core/services/centros-custo.service';
import { Portuguese } from 'flatpickr/dist/l10n/pt';

@Component({
  selector: 'app-relatorio-viagens',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, FlatpickrModule],
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
      id_centro_custo: this.relatorioCentroCusto || null
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
        r.push(row.valoresPorCategoria ? (row.valoresPorCategoria[cat] || 0) : 0);
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
}
