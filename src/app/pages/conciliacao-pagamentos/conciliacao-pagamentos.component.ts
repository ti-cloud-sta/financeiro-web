import { Component, signal, ViewChild, ElementRef, inject, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CardComponent } from '../../shared/components/card/card.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { IAuthService } from '../../core/interfaces/auth.service';
import { ImportacoesService, Importacao } from '../../core/services/importacoes.service';

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-conciliacao-pagamentos',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    CardComponent,
    ButtonComponent,
    ModalComponent,
    LoadingComponent,
    ConfirmModalComponent
  ],
  templateUrl: './conciliacao-pagamentos.component.html',
  styleUrl: './conciliacao-pagamentos.component.scss'
})
export class ConciliacaoPagamentosComponent implements OnInit {
  importacoesService = inject(ImportacoesService);
  authService = inject(IAuthService);

  // Confirm/Alert Modal State
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

  extractErrorMessage(err: any): string {
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

  @ViewChild('apbFileInput') apbFileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('bancoFileInput') bancoFileInput!: ElementRef<HTMLInputElement>;

  // Sidebar Menu Selection
  activeMenu = signal<string>('conciliar');

  isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') !== null
    ? localStorage.getItem('sidebarCollapsed') === 'true'
    : false;

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }

  // Menu Definition
  menus = signal<MenuItem[]>([
    { id: 'conciliar', label: 'Conciliações', icon: 'fa-solid fa-scale-balanced' }
  ]);

  // Import State Variables
  selectedFileApb = signal<File | null>(null);
  selectedFilesBanco = signal<File[]>([]);
  
  // Progress/Process State
  isProcessing = signal<boolean>(false);
  processingStep = signal<number>(0);
  processingText = signal<string>('');

  // History Search
  searchConciliacao = signal<string>('');

  // History List — mostra somente as colunas reais da tabela `importacoes`.
  conciliacaoHistory = signal<Importacao[]>([]);

  filteredConciliacaoHistory = computed(() => {
    const term = this.searchConciliacao().toLowerCase().trim();
    if (!term) return this.conciliacaoHistory();
    return this.conciliacaoHistory().filter(h =>
      h.nomeArquivo.toLowerCase().includes(term) ||
      h.tipo.toLowerCase().includes(term) ||
      (h.empresa?.nome || '').toLowerCase().includes(term)
    );
  });

  ngOnInit() {
    this.carregarHistorico();
  }

  carregarHistorico() {
    this.importacoesService.listar(1, 50, undefined, 'Conciliação Bancária').subscribe({
      next: (res) => this.conciliacaoHistory.set(res.items || []),
      error: (err) => console.error('Erro ao carregar historico de conciliações:', err)
    });
  }

  formatarData(dataIso: string): string {
    const d = new Date(dataIso);
    if (isNaN(d.getTime())) return dataIso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  excluirConciliacao(id: number) {
    this.openConfirmModal(
      'Confirmar Exclusão',
      'Tem certeza que deseja excluir esta conciliação? Esta ação é irreversível.',
      () => {
        this.closeConfirmModal();
        this.importacoesService.excluir(id).subscribe({
          next: () => {
            this.carregarHistorico();
          },
          error: (err) => {
            console.error('Erro ao excluir conciliação', err);
            this.openAlert('Erro', 'Não foi possível excluir o registro.', 'danger');
          }
        });
      },
      'danger'
    );
  }

  selectMenu(menuId: string) {
    this.activeMenu.set(menuId);
  }

  triggerUpload(type: 'apb' | 'banco') {
    if (type === 'apb' && this.apbFileInput) {
      this.apbFileInput.nativeElement.value = '';
      this.apbFileInput.nativeElement.click();
    } else if (type === 'banco' && this.bancoFileInput) {
      this.bancoFileInput.nativeElement.value = '';
      this.bancoFileInput.nativeElement.click();
    }
  }

  onFileSelected(event: Event, type: 'apb' | 'banco') {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      if (type === 'apb') {
        const file = input.files[0];
        this.selectedFileApb.set(file);
        this.lerPlanilhaApb(file);
      } else {
        const filesArray = Array.from(input.files);
        this.selectedFilesBanco.update(existing => {
          const jaSelecionados = new Set(existing.map(f => `${f.name}_${f.size}`));
          const novos = filesArray.filter(f => !jaSelecionados.has(`${f.name}_${f.size}`));
          if (novos.length < filesArray.length) {
            this.openAlert('Arquivo Duplicado', 'Um ou mais arquivos selecionados já estavam na lista e foram ignorados.', 'primary');
          }
          return [...existing, ...novos];
        });
      }
    }
  }

  lerPlanilhaApb(file: File) {
    this.importacoesService.lerApb(file).subscribe({
      next: (res) => {
        console.log('=== LISTA DE PESSOAS CONSOLIDADAS (PLANILHA APB) ===');
        console.log(res.dados);
        console.log('====================================================');
      },
      error: (err) => {
        console.error('Erro ao ler a planilha APB:', err);
        const detail = this.extractErrorMessage(err);
        this.openAlert('Erro no Processamento', `Não foi possível processar a planilha APB:\n${detail}`, 'danger');
      }
    });
  }

  removeBancoFile(index: number) {
    this.selectedFilesBanco.update(files => files.filter((_, i) => i !== index));
  }

  processarCruzamento() {
    const planilha = this.selectedFileApb();
    const extratos = this.selectedFilesBanco();

    if (!planilha || extratos.length === 0) return;

    this.isProcessing.set(true);
    this.processingStep.set(1);
    this.processingText.set('Enviando planilha e extratos bancários...');

    this.importacoesService.conciliarBancos(planilha, extratos, this.authService.currentUser()?.iduser).subscribe({
      next: (blob) => {
        this.isProcessing.set(false);

        // Baixa a mesma planilha recebida, agora com a coluna A preenchida
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = planilha.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.selectedFileApb.set(null);
        this.selectedFilesBanco.set([]);
        this.carregarHistorico();
      },
      error: (err) => {
        this.isProcessing.set(false);
        console.error('Erro ao conciliar extratos bancários:', err);
        const detail = this.extractErrorMessage(err);
        this.openAlert('Erro na Conciliação', `Não foi possível conciliar os extratos:\n${detail}`, 'danger');
      }
    });
  }
}
