import { Component, OnInit, signal, computed, ViewChild, ElementRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PendenciasComponent } from './components/pages/pendencias/pendencias.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { ImportacoesService, Importacao, ImportacaoPendenciasResponse } from '../../core/services/importacoes.service';

@Component({
  selector: 'app-inadimplencia',
  standalone: true,
  imports: [CommonModule, FormsModule, PendenciasComponent, ButtonComponent, ConfirmModalComponent],
  templateUrl: './inadimplencia.component.html',
  styleUrls: ['./inadimplencia.component.scss']
})
export class InadimplenciaComponent implements OnInit {
  private importacoesService = inject(ImportacoesService);

  isSidebarCollapsed = false;
  activeTab = 'pendencias';

  ngOnInit() {
    this.isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    this.carregarHistoricoAtualizacao();
  }

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  setActiveTab(tab: string) {
    this.activeTab = tab;
  }

  // ----------------------------------------------------
  // Atualização de Dados
  // ----------------------------------------------------
  @ViewChild('atualizacaoFileInput') atualizacaoFileInput!: ElementRef<HTMLInputElement>;
  @ViewChild(PendenciasComponent) pendenciasComponent?: PendenciasComponent;

  selectedFileAtualizacao = signal<File | null>(null);
  searchAtualizacao = signal<string>('');
  atualizacaoHistory = signal<Importacao[]>([]);
  isImportandoDados = signal<boolean>(false);

  filteredAtualizacaoHistory = computed(() => {
    const term = this.searchAtualizacao().toLowerCase().trim();
    if (!term) return this.atualizacaoHistory();
    return this.atualizacaoHistory().filter(h =>
      h.nomeArquivo.toLowerCase().includes(term) ||
      h.tipo.toLowerCase().includes(term)
    );
  });

  carregarHistoricoAtualizacao() {
    this.importacoesService.listar(1, 50, undefined, 'PENDENCIAS').subscribe({
      next: (res) => this.atualizacaoHistory.set(res.items || []),
      error: (err) => console.error('Erro ao carregar historico de atualizações de dados:', err)
    });
  }

  formatarData(dataIso: string): string {
    const d = new Date(dataIso);
    if (isNaN(d.getTime())) return dataIso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  triggerUploadAtualizacao() {
    if (this.atualizacaoFileInput) {
      this.atualizacaoFileInput.nativeElement.value = '';
      this.atualizacaoFileInput.nativeElement.click();
    }
  }

  onFileSelectedAtualizacao(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFileAtualizacao.set(input.files[0]);
    }
  }

  processarAtualizacaoDados() {
    const arquivo = this.selectedFileAtualizacao();
    if (!arquivo || this.isImportandoDados()) return;

    this.isImportandoDados.set(true);
    this.importacoesService.importarPendenciasInadimplencia(arquivo).subscribe({
      next: (res) => {
        this.isImportandoDados.set(false);
        this.selectedFileAtualizacao.set(null);
        this.carregarHistoricoAtualizacao();
        this.pendenciasComponent?.carregarPendencias();
        this.openAlert('Importação Concluída', this.montarResumoImportacao(res), 'primary');
      },
      error: (err) => {
        this.isImportandoDados.set(false);
        console.error('Erro ao importar pendências:', err);
        this.openAlert('Erro na Importação', this.extractErrorMessage(err), 'danger');
      }
    });
  }

  private montarResumoImportacao(res: ImportacaoPendenciasResponse): string {
    const linhas = [
      `Linhas com título: ${res.totalLinhasComEspecie}`,
      `Importadas: ${res.importadas}`,
      `Marcadas para análise (sem regra específica): ${res.classificadasPorFallback}`,
      `Ignoradas duplicadas: ${res.ignoradasDuplicadas}`,
      `Ignoradas sem vencimento: ${res.ignoradasSemVencimento}`,
      `Clientes criados: ${res.clientesCriados}`,
      `Matrizes criadas: ${res.matrizesCriadas}`,
      `Finalizadas automaticamente (sumiram da planilha): ${res.finalizadasAutomaticamente}`
    ];
    return linhas.join('\n');
  }

  private extractErrorMessage(err: any): string {
    if (err && err.error) {
      if (typeof err.error.detail === 'string') {
        return err.error.detail;
      }
      if (Array.isArray(err.error.detail)) {
        return err.error.detail.map((d: any) => `${d.loc?.join('.') || ''}: ${d.msg}`).join('\n');
      }
      if (err.error.message) {
        return err.error.message;
      }
    }
    return err.message || 'Erro desconhecido no servidor';
  }

  excluirAtualizacao(id: number) {
    this.openConfirmModal(
      'Confirmar Exclusão',
      'Tem certeza que deseja excluir esta atualização? Esta ação é irreversível.',
      () => {
        this.closeConfirmModal();
        this.importacoesService.excluir(id).subscribe({
          next: () => {
            this.carregarHistoricoAtualizacao();
          },
          error: (err) => {
            console.error('Erro ao excluir atualização de dados', err);
            this.openAlert('Erro', 'Não foi possível excluir o registro.', 'danger');
          }
        });
      },
      'danger'
    );
  }

  // ----------------------------------------------------
  // Confirm/Alert Modal (genérico)
  // ----------------------------------------------------
  isConfirmModalOpen = false;
  confirmTitle = '';
  confirmMessage = '';
  confirmText = 'Confirmar';
  cancelText = 'Cancelar';
  confirmVariant: 'danger' | 'primary' = 'primary';
  showCancelConfirm = true;
  confirmCallback: () => void = () => {};

  openConfirmModal(title: string, message: string, onConfirm: () => void, variant: 'danger' | 'primary' = 'danger') {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmText = 'Confirmar';
    this.cancelText = 'Cancelar';
    this.confirmVariant = variant;
    this.showCancelConfirm = true;
    this.confirmCallback = onConfirm;
    this.isConfirmModalOpen = true;
  }

  openAlert(title: string, message: string, variant: 'danger' | 'primary' = 'primary') {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmText = 'Ok';
    this.cancelText = '';
    this.confirmVariant = variant;
    this.showCancelConfirm = false;
    this.confirmCallback = () => this.closeConfirmModal();
    this.isConfirmModalOpen = true;
  }

  closeConfirmModal() {
    this.isConfirmModalOpen = false;
  }

  executeConfirm() {
    this.confirmCallback();
  }
}
