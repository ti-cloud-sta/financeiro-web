import { Component, signal, ViewChild, ElementRef, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { CardComponent } from '../../shared/components/card/card.component';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { ImportacoesService, Importacao } from '../../core/services/importacoes.service';
import { IAuthService } from '../../core/interfaces/auth.service';

export interface ExtractorCard {
  id: string;
  name: string;
  description: string;
  icon: string;
  logo?: string;
  colorClass: string;
  status: 'active' | 'upcoming' | 'maintenance';
  statusText: string;
  statusVariant: 'success' | 'warning' | 'info' | 'primary' | 'secondary' | 'error' | 'danger';
}

@Component({
  selector: 'app-extratores',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    CardComponent,
    BadgeComponent,
    ButtonComponent,
    ModalComponent,
    LoadingComponent
  ],
  templateUrl: './extratores.component.html',
  styleUrl: './extratores.component.scss'
})
export class ExtratoresComponent implements OnInit {
  authService = inject(IAuthService);
  private importacoesService = inject(ImportacoesService);

  // Estado de upload Unificado para Composições
  isComposicaoUnifiedModalOpen = false;
  composicaoExtSelecionado: ExtractorCard | null = null;
  composicaoEmpresaFile = signal<File | null>(null);
  composicaoAcrFile = signal<File | null>(null);
  isComposicaoUnifiedProcessing = signal<boolean>(false);
  composicaoUnifiedError = signal<string>('');

  @ViewChild('composicaoEmpresaFileInput') composicaoEmpresaFileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('composicaoAcrFileInput') composicaoAcrFileInput!: ElementRef<HTMLInputElement>;

  isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') !== null
    ? localStorage.getItem('sidebarCollapsed') === 'true'
    : true;
  activeTab: 'composicoes' | 'prorrogacoes' = 'composicoes';

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  setActiveTab(tab: 'composicoes' | 'prorrogacoes') {
    this.activeTab = tab;
  }

  getComposicoesExtractors() {
    return this.extractors().filter(ext => !ext.id.includes('prorrogacao'));
  }

  getProrrogacoesExtractors() {
    return this.extractors().filter(ext => ext.id.includes('prorrogacao'));
  }

  historicoComposicoes = signal<Importacao[]>([]);
  historicoProrrogacoes = signal<Importacao[]>([]);

  ngOnInit() {
    this.carregarHistorico();
  }

  carregarHistorico() {
    this.importacoesService.listar(1, 50, undefined, 'Composição').subscribe({
      next: (res) => {
        this.historicoComposicoes.set(res.items);
      },
      error: (err) => console.error('Erro ao carregar composições', err)
    });

    this.importacoesService.listar(1, 50, undefined, 'Prorrogação').subscribe({
      next: (res) => {
        this.historicoProrrogacoes.set(res.items);
      },
      error: (err) => console.error('Erro ao carregar prorrogações', err)
    });
  }

  // Estado para o Modal de Exclusão
  isDeleteModalOpen = signal<boolean>(false);
  importacaoToDelete = signal<number | null>(null);

  confirmarExclusao(id: number, event: Event) {
    event.stopPropagation();
    this.importacaoToDelete.set(id);
    this.isDeleteModalOpen.set(true);
  }

  executarExclusao() {
    const id = this.importacaoToDelete();
    if (id !== null) {
      this.importacoesService.excluir(id).subscribe({
        next: () => {
          this.isDeleteModalOpen.set(false);
          this.importacaoToDelete.set(null);
          this.carregarHistorico();
        },
        error: (err) => {
          console.error('Erro ao excluir importação', err);
          this.isDeleteModalOpen.set(false);
        }
      });
    }
  }

  cancelarExclusao() {
    this.isDeleteModalOpen.set(false);
    this.importacaoToDelete.set(null);
  }


  extractors = signal<ExtractorCard[]>([
    {
      id: 'ext-pdf-ia',
      name: 'Atacadão',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-wand-magic-sparkles',
      logo: 'https://ecofresh.com.br/wp-content/uploads/2022/01/encontrar-logo2.png',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-ofx-pdf',
      name: 'Sendas',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAv6n6zkzPBoXUjsrw0ds816MvJ7LBx5jlAILlEediDg&s',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-martminas-composicao',
      name: 'Mart Minas',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRk7-Tv6nykbMNJhwJyk9USvr9mu-IYytniXe8p8hdUFf1UoBo-eudhKhb9&s=10',
      colorClass: 'text-danger bg-danger-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-savegnago-composicao',
      name: 'Savegnago',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://yt3.googleusercontent.com/tpbXCW_NY8lzg1FhWCoft7dfRe4I837NeH48hNfa2kQAdKVmqkjYX1aNshon2s8XDBZPgRr1Dg=s900-c-k-c0x00ffffff-no-rj',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-cema-composicao',
      name: 'Cema',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://d2q79iu7y748jz.cloudfront.net/s/_squarelogo/256x256/4adbeb4dd0076c044afd87f8cc9dda97',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-mateus-composicao',
      name: 'Mateus',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://images.seeklogo.com/logo-png/20/1/grupo-mateus-logo-png_seeklogo-207578.png',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-drogaraia-composicao',
      name: 'Droga Raia',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRJyK8qtV1gCvyfin2YuX-W9c4lKeI5OgqijKcqdcaNQA&s=10',
      colorClass: 'text-danger bg-danger-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-amazon-composicao',
      name: 'Amazon',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg',
      colorClass: 'text-warning bg-warning-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-gpa-composicao',
      name: 'GPA',
      description: 'Importação de dados da composição de pagamento',
      icon: 'fa-solid fa-file-excel',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDWJcB0nVZmbH3hxE0N672dnh0ehHozhAT4TzbRN0vqg&s=10',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-atacadao-prorrogacao',
      name: 'Atacadão',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://ecofresh.com.br/wp-content/uploads/2022/01/encontrar-logo2.png',
      colorClass: 'text-info bg-info-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-sendas-prorrogacao',
      name: 'Sendas',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAv6n6zkzPBoXUjsrw0ds816MvJ7LBx5jlAILlEediDg&s',
      colorClass: 'text-warning bg-warning-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-martminas-prorrogacao',
      name: 'Mart Minas',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRk7-Tv6nykbMNJhwJyk9USvr9mu-IYytniXe8p8hdUFf1UoBo-eudhKhb9&s=10',
      colorClass: 'text-danger bg-danger-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-savegnago-prorrogacao',
      name: 'Savegnago',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://yt3.googleusercontent.com/tpbXCW_NY8lzg1FhWCoft7dfRe4I837NeH48hNfa2kQAdKVmqkjYX1aNshon2s8XDBZPgRr1Dg=s900-c-k-c0x00ffffff-no-rj',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-cema-prorrogacao',
      name: 'Cema',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://d2q79iu7y748jz.cloudfront.net/s/_squarelogo/256x256/4adbeb4dd0076c044afd87f8cc9dda97',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-mateus-prorrogacao',
      name: 'Mateus',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://images.seeklogo.com/logo-png/20/1/grupo-mateus-logo-png_seeklogo-207578.png',
      colorClass: 'text-primary bg-primary-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-drogaraia-prorrogacao',
      name: 'Droga Raia',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRJyK8qtV1gCvyfin2YuX-W9c4lKeI5OgqijKcqdcaNQA&s=10',
      colorClass: 'text-danger bg-danger-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-amazon-prorrogacao',
      name: 'Amazon',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg',
      colorClass: 'text-warning bg-warning-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    },
    {
      id: 'ext-gpa-prorrogacao',
      name: 'GPA',
      description: 'Importação de dados de prorrogação',
      icon: 'fa-solid fa-clock-rotate-left',
      logo: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDWJcB0nVZmbH3hxE0N672dnh0ehHozhAT4TzbRN0vqg&s=10',
      colorClass: 'text-success bg-success-subtle',
      status: 'active',
      statusText: 'Ativo',
      statusVariant: 'success'
    }
  ]);

  @ViewChild('prorrogacaoHtmlInput') prorrogacaoHtmlInput!: ElementRef<HTMLInputElement>;
  @ViewChild('prorrogacaoExcelInput') prorrogacaoExcelInput!: ElementRef<HTMLInputElement>;

  // Estado de upload da Prorrogação (Atacadão)
  prorrogacaoHtmlFiles = signal<File[]>([]);
  prorrogacaoExcelFile = signal<File | null>(null);
  isProrrogacaoModalOpen = signal<boolean>(false);
  isProrrogacaoProcessing = signal<boolean>(false);
  prorrogacaoError = signal<string>('');

  @ViewChild('sendasProrrogacaoInput') sendasProrrogacaoInput!: ElementRef<HTMLInputElement>;
  @ViewChild('acrProrrogacaoInput') acrProrrogacaoInput!: ElementRef<HTMLInputElement>;

  // Estado de upload da Prorrogação Sendas (Sendas + ACR)
  sendasProrrogacaoFile = signal<File | null>(null);
  acrProrrogacaoFile = signal<File | null>(null);
  isSendasProrrogacaoModalOpen = signal<boolean>(false);
  isSendasProrrogacaoProcessing = signal<boolean>(false);
  sendasProrrogacaoError = signal<string>('');

  @ViewChild('martminasProrrogacaoInput') martminasProrrogacaoInput!: ElementRef<HTMLInputElement>;
  @ViewChild('acrMartminasProrrogacaoInput') acrMartminasProrrogacaoInput!: ElementRef<HTMLInputElement>;

  // Estado de upload da Prorrogação Mart Minas (Mart Minas + ACR)
  martminasProrrogacaoFile = signal<File | null>(null);
  acrMartminasProrrogacaoFile = signal<File | null>(null);
  isMartminasProrrogacaoModalOpen = signal<boolean>(false);
  isMartminasProrrogacaoProcessing = signal<boolean>(false);
  martminasProrrogacaoError = signal<string>('');

  @ViewChild('savegnagoProrrogacaoInput') savegnagoProrrogacaoInput!: ElementRef<HTMLInputElement>;
  @ViewChild('acrSavegnagoProrrogacaoInput') acrSavegnagoProrrogacaoInput!: ElementRef<HTMLInputElement>;

  // Estado de upload da Prorrogação Savegnago (Savegnago + ACR)
  savegnagoProrrogacaoFile = signal<File | null>(null);
  acrSavegnagoProrrogacaoFile = signal<File | null>(null);
  isSavegnagoProrrogacaoModalOpen = signal<boolean>(false);
  isSavegnagoProrrogacaoProcessing = signal<boolean>(false);
  savegnagoProrrogacaoError = signal<string>('');

  // =========================================================
  // Modal Unificado de Prorrogação
  // =========================================================
  isProrrogacaoUnifiedModalOpen = false;
  prorrogacaoExtSelecionado: ExtractorCard | null = null;
  prorrogacaoEmpresaFiles = signal<File[]>([]);
  prorrogacaoAcrFile = signal<File | null>(null);
  isProrrogacaoUnifiedProcessing = signal<boolean>(false);
  prorrogacaoUnifiedError = signal<string>('');

  @ViewChild('prorrogacaoEmpresaFileInput') prorrogacaoEmpresaFileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('prorrogacaoAcrFileInput') prorrogacaoAcrFileInput!: ElementRef<HTMLInputElement>;

  openProrrogacaoModal(ext: ExtractorCard) {
    this.prorrogacaoExtSelecionado = ext;
    this.prorrogacaoEmpresaFiles.set([]);
    this.prorrogacaoAcrFile.set(null);
    this.isProrrogacaoUnifiedProcessing.set(false);
    this.prorrogacaoUnifiedError.set('');
    this.isProrrogacaoUnifiedModalOpen = true;
  }

  closeProrrogacaoModal() {
    if (!this.isProrrogacaoUnifiedProcessing()) {
      this.isProrrogacaoUnifiedModalOpen = false;
      this.prorrogacaoExtSelecionado = null;
    }
  }

  triggerProrrogacaoEmpresaFileInput() {
    if (this.prorrogacaoEmpresaFileInput) {
      this.prorrogacaoEmpresaFileInput.nativeElement.click();
    }
  }

  triggerProrrogacaoAcrFileInput() {
    if (this.prorrogacaoAcrFileInput) {
      this.prorrogacaoAcrFileInput.nativeElement.click();
    }
  }

  onProrrogacaoEmpresaFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.prorrogacaoEmpresaFiles.set(Array.from(input.files));
    }
  }

  onProrrogacaoAcrFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.prorrogacaoAcrFile.set(input.files[0]);
    }
  }

  getEmpresaFileAccept(): string {
    if (this.prorrogacaoExtSelecionado?.id === 'ext-atacadao-prorrogacao') {
      return '.html,.htm';
    }
    return '.xlsx,.xls';
  }

  processProrrogacaoUnified() {
    const empresaFiles = this.prorrogacaoEmpresaFiles();
    const acrFile = this.prorrogacaoAcrFile();
    if (empresaFiles.length === 0 || !acrFile) {
      this.prorrogacaoUnifiedError.set('Por favor, selecione ambos os arquivos antes de processar.');
      return;
    }

    this.isProrrogacaoUnifiedProcessing.set(true);
    this.prorrogacaoUnifiedError.set('');

    const extId = this.prorrogacaoExtSelecionado?.id;
    const empresaFile = empresaFiles[0];

    // Redirecionar para o método correto de acordo com a empresa
    if (extId === 'ext-atacadao-prorrogacao') {
      this.prorrogacaoHtmlFiles.set(empresaFiles);
      this.prorrogacaoExcelFile.set(acrFile);
      this._processAtacadaoProrrogacao();
    } else if (extId === 'ext-sendas-prorrogacao') {
      this.sendasProrrogacaoFile.set(empresaFile);
      this.acrProrrogacaoFile.set(acrFile);
      this._processSendasProrrogacao();
    } else if (extId === 'ext-martminas-prorrogacao') {
      this.martminasProrrogacaoFile.set(empresaFile);
      this.acrMartminasProrrogacaoFile.set(acrFile);
      this._processMartminasProrrogacao();
    } else if (extId === 'ext-savegnago-prorrogacao') {
      this.savegnagoProrrogacaoFile.set(empresaFile);
      this.acrSavegnagoProrrogacaoFile.set(acrFile);
      this._processSavegnagoProrrogacao();
    } else if (extId === 'ext-cema-prorrogacao') {
      this._processCemaProrrogacao(empresaFile, acrFile);
    } else if (extId === 'ext-mateus-prorrogacao') {
      this._processMateusProrrogacao(empresaFile, acrFile);
    } else if (extId === 'ext-drogaraia-prorrogacao') {
      this._processDrogaRaiaProrrogacao(empresaFile, acrFile);
    } else if (extId === 'ext-amazon-prorrogacao') {
      this._processAmazonProrrogacao(empresaFile, acrFile);
    } else if (extId === 'ext-gpa-prorrogacao') {
      this._processGPAProrrogacao(empresaFile, acrFile);
    }
  }

  private _processAmazonProrrogacao(empresa: File, acr: File) {
    this.prorrogacaoUnifiedError.set('A funcionalidade de conciliação da Amazon ainda está aguardando os critérios de negócio.');
    this.isProrrogacaoUnifiedProcessing.set(false);
  }

  private _processGPAProrrogacao(empresa: File, acr: File) {
    this.prorrogacaoUnifiedError.set('A funcionalidade de conciliação do GPA ainda está aguardando os critérios de negócio.');
    this.isProrrogacaoUnifiedProcessing.set(false);
  }

  private _processDrogaRaiaProrrogacao(empresa: File, acr: File) {
    this.importacoesService.conciliarProrrogacaoDrogaRaia(empresa, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = empresa.name.substring(0, empresa.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }

  private _processMateusProrrogacao(empresa: File, acr: File) {
    this.importacoesService.conciliarProrrogacaoMateus(empresa, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = empresa.name.substring(0, empresa.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }

  private _processCemaProrrogacao(empresa: File, acr: File) {
    this.importacoesService.conciliarProrrogacaoCema(empresa, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = empresa.name.substring(0, empresa.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }

  private _downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  private _processAtacadaoProrrogacao() {
    const htmls = this.prorrogacaoHtmlFiles();
    const csv = this.prorrogacaoExcelFile()!;
    this.importacoesService.conciliarProrrogacaoAtacadao(htmls, csv, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = htmls[0].name.substring(0, htmls[0].name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato do HTML e do CSV está correto.');
      }
    });
  }

  private _processSendasProrrogacao() {
    const sendas = this.sendasProrrogacaoFile()!;
    const acr = this.acrProrrogacaoFile()!;
    this.importacoesService.conciliarProrrogacaoSendas(sendas, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = sendas.name.substring(0, sendas.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }

  private _processMartminasProrrogacao() {
    const martminas = this.martminasProrrogacaoFile()!;
    const acr = this.acrMartminasProrrogacaoFile()!;
    this.importacoesService.conciliarProrrogacaoMartminas(martminas, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = martminas.name.substring(0, martminas.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }

  private _processSavegnagoProrrogacao() {
    const savegnago = this.savegnagoProrrogacaoFile()!;
    const acr = this.acrSavegnagoProrrogacaoFile()!;
    this.importacoesService.conciliarProrrogacaoSavegnago(savegnago, acr, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.carregarHistorico();
        this.isProrrogacaoUnifiedProcessing.set(false);
        this.isProrrogacaoUnifiedModalOpen = false;
        const originalName = savegnago.name.substring(0, savegnago.name.lastIndexOf('.')) || 'Conciliado';
        this._downloadBlob(blob, `${originalName}_conciliado.xlsx`);
      },
      error: (err) => {
        this.isProrrogacaoUnifiedProcessing.set(false);
        console.error(err);
        this.prorrogacaoUnifiedError.set('Erro ao conciliar os arquivos. Verifique se o formato das planilhas está correto.');
      }
    });
  }


  openComposicaoModal(ext: ExtractorCard) {
    this.composicaoExtSelecionado = ext;
    this.composicaoEmpresaFile.set(null);
    this.composicaoAcrFile.set(null);
    this.composicaoUnifiedError.set('');
    this.isComposicaoUnifiedProcessing.set(false);
    this.isComposicaoUnifiedModalOpen = true;
  }

  closeComposicaoModal() {
    this.isComposicaoUnifiedModalOpen = false;
    this.composicaoExtSelecionado = null;
  }

  triggerComposicaoEmpresaFileInput() {
    if (this.composicaoEmpresaFileInput) {
      this.composicaoEmpresaFileInput.nativeElement.click();
    }
  }

  triggerComposicaoAcrFileInput() {
    if (this.composicaoAcrFileInput) {
      this.composicaoAcrFileInput.nativeElement.click();
    }
  }

  onComposicaoEmpresaFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.composicaoEmpresaFile.set(input.files[0]);
    }
  }

  onComposicaoAcrFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.composicaoAcrFile.set(input.files[0]);
    }
  }

  processComposicaoUnified() {
    if (!this.composicaoEmpresaFile() || !this.composicaoAcrFile() || !this.composicaoExtSelecionado) return;

    this.isComposicaoUnifiedProcessing.set(true);
    this.composicaoUnifiedError.set('');

    const empresaFile = this.composicaoEmpresaFile()!;
    const acrFile = this.composicaoAcrFile()!;
    const extId = this.composicaoExtSelecionado.id;
    let requestObservable: Observable<Blob>;
    
    switch (extId) {
      case 'ext-pdf-ia':
        requestObservable = this.importacoesService.extrairAtacadao(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-ofx-pdf':
        requestObservable = this.importacoesService.extrairSendas(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-martminas-composicao':
        requestObservable = this.importacoesService.extrairMartMinas(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-savegnago-composicao':
        requestObservable = this.importacoesService.extrairSavegnago(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-cema-composicao':
        requestObservable = this.importacoesService.extrairCema(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-mateus-composicao':
        requestObservable = this.importacoesService.extrairMateus(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-drogaraia-composicao':
        requestObservable = this.importacoesService.extrairDrogaRaia(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-amazon-composicao':
        requestObservable = this.importacoesService.extrairAmazon(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      case 'ext-gpa-composicao':
        requestObservable = this.importacoesService.extrairGPA(empresaFile, acrFile, this.authService.currentUser()?.iduser);
        break;
      default:
        this.composicaoUnifiedError.set('Funcionalidade ainda não implementada.');
        this.isComposicaoUnifiedProcessing.set(false);
        return;
    }

    requestObservable.subscribe({
      next: (blob: Blob) => {
        this.carregarHistorico();
        this.isComposicaoUnifiedProcessing.set(false);
        this.isComposicaoUnifiedModalOpen = false;
        
        const originalName = empresaFile.name.substring(0, empresaFile.name.lastIndexOf('.')) || 'Conciliado';
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `${originalName}_Conciliado.xlsx`;
        link.click();
        window.URL.revokeObjectURL(link.href);

        this.composicaoEmpresaFile.set(null);
        this.composicaoAcrFile.set(null);
      },
      error: (err: any) => {
        this.isComposicaoUnifiedProcessing.set(false);
        console.error(err);
        this.composicaoUnifiedError.set('Erro ao processar a planilha. Verifique se as colunas estão corretas.');
      }
    });
  }
}
