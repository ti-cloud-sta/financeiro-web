import { computed, signal } from '@angular/core';
import { IAuthService } from '../../core/interfaces/auth.service';
import { User } from '../../core/models/user.model';
import { of } from 'rxjs';
import { Component, inject, OnInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, FormsModule } from '@angular/forms';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';

import { ButtonComponent } from '../../shared/components/button/button.component';
import { InputComponent } from '../../shared/components/input/input.component';
import { ModalComponent } from '../../shared/components/modal/modal.component';
import { ConfirmModalComponent } from '../../shared/components/confirm-modal/confirm-modal.component';
import { DropdownComponent } from '../../shared/components/dropdown/dropdown.component';
import { BadgeComponent } from '../../shared/components/badge/badge.component';

import {
  ColaboradoresService, Colaborador,
  ImportPreviewResponse, ImportProcessarResponse, ImportNovo, ImportDivergente, ImportDesligado
} from '../../core/services/colaboradores.service';
import { CategoriasService, Categoria } from '../../core/services/categorias.service';
import { CargosColaboradoresService, CargoColaborador } from '../../core/services/cargos-colaboradores.service';
import { CentrosCustoService, CentroCusto } from '../../core/services/centros-custo.service';
import { UnidadesService, Unidade } from '../../core/services/unidades.service';
import { EmpresasService, Empresa } from '../../core/services/empresas.service';

@Component({
  selector: 'app-configuracoes-cadastros',
  standalone: true,
  imports: [
    NgSelectModule,
    CommonModule, ReactiveFormsModule, FormsModule,
    EmptyStateComponent, ButtonComponent, InputComponent,
    ModalComponent, ConfirmModalComponent, DropdownComponent,
    BadgeComponent
  ],
  templateUrl: './configuracoes-cadastros.component.html',
  styleUrl: './configuracoes-cadastros.component.scss'
})
export class ConfiguracoesCadastrosComponent implements OnInit {
  modulosOptions = [
    { id: 1, nome: 'Despesas de Viagens' },
    { id: 2, nome: 'Plano de Saúde' },
    { id: 3, nome: 'Extratores' },
    { id: 4, nome: 'Inadimplência' },
    { id: 5, nome: 'Conciliação de Pagamentos' }
  ];

  private authService = inject(IAuthService);
  isAdmin = computed(() => this.authService.currentUser()?.role === 'admin');

  users = signal<User[]>([]);
  searchTermUsuarios = '';
  get filteredUsers(): User[] {
    const term = this.searchTermUsuarios.toLowerCase();
    return this.users().filter(u => 
      u.name.toLowerCase().includes(term) || 
      u.email.toLowerCase().includes(term)
    );
  }

  onSearchUsuariosChange(val: string) {
    this.searchTermUsuarios = val;
  }

  carregarUsuarios() {
    // Mock users just to render
    this.users.set([
      { id: '1', name: 'Admin User', email: 'admin@stamaria.ind.br', role: 'admin', active: 'S' },
      { id: '2', name: 'Default User', email: 'default@stamaria.ind.br', role: 'user', active: 'S' }
    ]);
  }

  isCadastroModalOpen = false;
  isPasswordModalOpen = false;
  selectedUser: User | null = null;
  cadastroForm: FormGroup;
  passwordForm: FormGroup;

  constructor() {
    const fb = inject(FormBuilder);
    this.cadastroForm = fb.group({
      name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', Validators.required]
    }, { validators: this.passwordMatchValidator });

    this.passwordForm = fb.group({
      newPassword: ['', [Validators.required, Validators.minLength(6)]],
      confirmNewPassword: ['', Validators.required]
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(g: FormGroup) {
    const p = g.get('password') || g.get('newPassword');
    const cp = g.get('confirmPassword') || g.get('confirmNewPassword');
    return p && cp && p.value === cp.value ? null : { mismatch: true };
  }

  openCadastroModal() {
    this.cadastroForm.reset();
    this.isCadastroModalOpen = true;
  }
  closeCadastroModal() {
    this.isCadastroModalOpen = false;
  }
  onCadastroSubmit() {
    if (this.cadastroForm.invalid) return;
    this.closeCadastroModal();
  }

  openPasswordModal(user: User) {
    this.selectedUser = user;
    this.passwordForm.reset();
    this.isPasswordModalOpen = true;
  }
  closePasswordModal() {
    this.isPasswordModalOpen = false;
    this.selectedUser = null;
  }
  onPasswordSubmit() {
    if (this.passwordForm.invalid) return;
    this.closePasswordModal();
  }

  confirmGrantAdmin(user: User) {
    this.openConfirmModal('Alterar Acesso', `Deseja ${user.role === 'admin' ? 'remover' : 'conceder'} acesso de administrador para ${user.name}?`, () => {
      this.users.update(users => users.map(u => {
        if (u.id === user.id) {
          return { ...u, role: u.role === 'admin' ? 'user' : 'admin' };
        }
        return u;
      }));
      this.closeConfirmModal();
    });
  }

  confirmToggleBlockUser(user: User) {
    const isBlocked = user.active === 'N';
    const action = isBlocked ? 'desbloquear' : 'bloquear';
    this.openConfirmModal(
      isBlocked ? 'Desbloquear Usuário' : 'Bloquear Usuário',
      `Tem certeza que deseja ${action} o usuário ${user.name}?`,
      () => {
        this.users.update(users => users.map(u => {
          if (u.id === user.id) {
            return { ...u, active: isBlocked ? 'S' : 'N' };
          }
          return u;
        }));
        this.closeConfirmModal();
      }
    );
  }

  private fb = inject(FormBuilder);

  private colaboradoresService = inject(ColaboradoresService);
  private categoriasService = inject(CategoriasService);
  private cargosService = inject(CargosColaboradoresService);
  private centrosCustoService = inject(CentrosCustoService);
  private unidadesService = inject(UnidadesService);
  private empresasService = inject(EmpresasService);

  // Confirm modal state
  isConfirmModalOpen = false;
  isConfirmLoading = false;
  confirmTitle = '';
  confirmMessage = '';
  confirmCallback: (() => void) | null = null;

  openConfirmModal(title: string, message: string, callback: () => void) {
    this.confirmTitle = title;
    this.confirmMessage = message;
    this.confirmCallback = callback;
    this.isConfirmModalOpen = true;
    this.isConfirmLoading = false;
  }

  closeConfirmModal() {
    this.isConfirmModalOpen = false;
    this.isConfirmLoading = false;
    this.confirmCallback = null;
  }

  onConfirm() {
    if (this.confirmCallback) {
      this.isConfirmLoading = true;
      this.confirmCallback();
    }
  }

  // Tab state
  activeConfigTab: 'colaboradores' | 'categorias' | 'cargos' | 'centros-custo' | 'unidades' | 'empresas' | 'usuarios' = 'colaboradores';

  setActiveConfigTab(tab: typeof this.activeConfigTab) {
    this.activeConfigTab = tab;
  }

  ngOnInit(): void {
    this.carregarColaboradores();
    this.carregarCategorias();
    this.carregarCargos();
    this.carregarCentrosCusto();
    this.carregarUnidades();
    this.carregarEmpresasConfig();
    this.carregarColaboradoresGeral();
    this.carregarCategoriasGeral();
    this.carregarEmpresasGeral();
    this.carregarCentrosCustoGeral();
    this.carregarUnidadesGeral();
    this.carregarUsuarios();
  }

  // Sidebar state
  isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    localStorage.setItem('sidebarCollapsed', String(this.isSidebarCollapsed));
  }



  // CARGOS DE COLABORADOR
  // ==========================================
  listaCargos: CargoColaborador[] = [];
  isNovoCargoModalOpen = false;
  cargoModalMode: 'create' | 'edit' = 'create';
  novoCargo: any = { nome: '', descricao: '' };
  isSalvandoCargo = false;

  // ==========================================
  // UNIDADES
  // ==========================================
  searchUnidade = '';
  currentUnidadePage = 1;
  itemsUnidadePerPage = 10;
  totalUnidades = 0;
  totalUnidadePages = 1;
  listaUnidades: Unidade[] = [];
  listaUnidadesGeral: Unidade[] = [];

  unidadeModalMode: 'create' | 'edit' = 'create';
  isUnidadeModalOpen = false;
  novaUnidade: any = { codigo: null, descricao: '' };
  isSalvandoUnidade = false;

  carregarUnidades() {
    this.unidadesService.listar(this.currentUnidadePage, this.itemsUnidadePerPage, this.searchUnidade).subscribe({
      next: (res) => {
        this.listaUnidades = res.items;
        this.totalUnidades = res.total;
        this.totalUnidadePages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar unidades', err)
    });
  }

  onSearchUnidadeChange(term: string) {
    this.searchUnidade = term;
    this.currentUnidadePage = 1;
    this.carregarUnidades();
  }

  carregarUnidadesGeral() {
    this.unidadesService.listar(1, 1000).subscribe({
      next: (res) => {
        this.listaUnidadesGeral = (res.items || []).sort((a, b) => (a.descricao || '').localeCompare(b.descricao || ''));
      }
    });
  }

  listaColaboradoresGeral: Colaborador[] = [];
  carregarColaboradoresGeral() {
    this.colaboradoresService.listar(1, 2000).subscribe({
      next: (res) => this.listaColaboradoresGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  listaCategoriasGeral: Categoria[] = [];
  carregarCategoriasGeral() {
    this.categoriasService.listar(1, 1000).subscribe({
      next: (res) => this.listaCategoriasGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  listaEmpresasGeral: any[] = [];
  carregarEmpresasGeral() {
    this.empresasService.listar(1, 1000, '').subscribe({
      next: (res) => this.listaEmpresasGeral = (res.items || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
    });
  }

  goToUnidadePage(page: number) {
    if (page >= 1 && page <= this.totalUnidadePages) {
      this.currentUnidadePage = page;
      this.carregarUnidades();
    }
  }

  openUnidadeModal(unidade?: Unidade) {
    if (unidade) {
      this.unidadeModalMode = 'edit';
      this.novaUnidade = { ...unidade };
    } else {
      this.unidadeModalMode = 'create';
      this.novaUnidade = { codigo: null, descricao: '' };
    }
    this.isUnidadeModalOpen = true;
  }

  closeUnidadeModal() {
    this.isUnidadeModalOpen = false;
  }

  salvarUnidade() {
    this.isSalvandoUnidade = true;
    if (this.unidadeModalMode === 'create') {
      this.unidadesService.criar(this.novaUnidade).subscribe({
        next: () => {
          this.isSalvandoUnidade = false;
          this.closeUnidadeModal();
          this.carregarUnidades();
          this.carregarUnidadesGeral();
    this.carregarUsuarios();
        },
        error: (err) => { console.error(err); this.isSalvandoUnidade = false; }
      });
    } else {
      this.unidadesService.atualizar(this.novaUnidade.idUnidade, this.novaUnidade).subscribe({
        next: () => {
          this.isSalvandoUnidade = false;
          this.closeUnidadeModal();
          this.carregarUnidades();
          this.carregarUnidadesGeral();
    this.carregarUsuarios();
        },
        error: (err) => { console.error(err); this.isSalvandoUnidade = false; }
      });
    }
  }

  confirmarExclusaoUnidade(id: number) {
    this.openConfirmModal('Excluir Unidade', 'Tem certeza que deseja excluir esta Unidade?', () => {
      this.unidadesService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarUnidades();
          this.carregarUnidadesGeral();
    this.carregarUsuarios();
        },
        error: (err) => {
          console.error(err);
          this.closeConfirmModal();
        }
      });
    });
  }

  carregarCargos() {
    this.cargosService.listar(1, 100).subscribe({
      next: (res) => this.listaCargos = res.items,
      error: (err) => console.error('Erro ao carregar cargos', err)
    });
  }

  openNovoCargoModal() {
    this.cargoModalMode = 'create';
    this.novoCargo = { nome: '', descricao: '' };
    this.isNovoCargoModalOpen = true;
  }

  closeNovoCargoModal() {
    this.isNovoCargoModalOpen = false;
  }

  editarCargo(cargo: CargoColaborador) {
    this.cargoModalMode = 'edit';
    this.novoCargo = { ...cargo };
  }

  cancelarEdicaoCargo() {
    this.cargoModalMode = 'create';
    this.novoCargo = { nome: '', descricao: '' };
  }

  salvarNovoCargo() {
    this.isSalvandoCargo = true;
    if (this.cargoModalMode === 'create') {
      this.cargosService.criar(this.novoCargo).subscribe({
        next: (cargo) => {
          if (cargo.idCargoColaborador) {
            this.novoColaborador.idCargoColaborador = cargo.idCargoColaborador;
          }
          this.isSalvandoCargo = false;
          this.carregarCargos();
          this.cancelarEdicaoCargo();
        },
        error: (err: any) => {
          console.error('Erro ao salvar cargo', err);
          this.isSalvandoCargo = false;
        }
      });
    } else {
      this.cargosService.atualizar(this.novoCargo.idCargoColaborador, this.novoCargo).subscribe({
        next: () => {
          this.isSalvandoCargo = false;
          this.carregarCargos();
          this.cancelarEdicaoCargo();
        },
        error: (err: any) => {
          console.error('Erro ao atualizar cargo', err);
          this.isSalvandoCargo = false;
        }
      });
    }
  }

  confirmarExclusaoCargo(id: number) {
    this.openConfirmModal('Excluir Cargo de Vínculo', 'Tem certeza que deseja excluir este cargo? Caso existam colaboradores vinculados, você poderá ter problemas.', () => {
      this.cargosService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarCargos();
          // Se estava editando o mesmo que foi excluido, reseta
          if (this.novoCargo.idCargoColaborador === id) {
            this.cancelarEdicaoCargo();
          }
        },
        error: (err: any) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }

  // ==========================================
  // COLABORADORES
  // ==========================================
  searchTerm = '';
  currentPage = 1;
  itemsPerPage = 10;
  totalColaboradores = 0;
  totalPages = 1;
  listaColaboradores: Colaborador[] = [];

  colaboradorModalMode: 'create' | 'edit' = 'create';
  isColaboradorModalOpen = false;
  novoColaborador: any = { nome: '', idCentroCusto: null, idCargoColaborador: null, idUnidade: null, papel: '' };
  isSalvandoColaborador = false;

  getUnidadesCodigos(colab: Colaborador): string {
    return (colab.unidades || []).map(u => u.codigo).join(', ');
  }

  carregarColaboradores() {
    this.colaboradoresService.listar(this.currentPage, this.itemsPerPage, this.searchTerm).subscribe({
      next: (res) => {
        this.listaColaboradores = res.items;
        this.totalColaboradores = res.total;
        this.totalPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar colaboradores', err)
    });
  }

  onSearchChange(term: string) {
    this.searchTerm = term;
    this.currentPage = 1;
    this.carregarColaboradores();
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.carregarColaboradores();
    }
  }

  openColaboradorModal(colaborador?: Colaborador) {
    if (colaborador) {
      this.colaboradorModalMode = 'edit';
      this.novoColaborador = { ...colaborador };
    } else {
      this.colaboradorModalMode = 'create';
      this.novoColaborador = { nome: '', idCentroCusto: null, idCargoColaborador: null, idUnidade: null, papel: '' };
    }
    this.isColaboradorModalOpen = true;
  }

  closeColaboradorModal() {
    this.isColaboradorModalOpen = false;
  }

  salvarColaborador() {
    this.isSalvandoColaborador = true;
    if (this.colaboradorModalMode === 'create') {
      this.colaboradoresService.criar(this.novoColaborador).subscribe({
        next: () => {
          this.isSalvandoColaborador = false;
          this.closeColaboradorModal();
          this.carregarColaboradores();
          this.carregarColaboradoresGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoColaborador = false; }
      });
    } else {
      this.colaboradoresService.atualizar(this.novoColaborador.idColaborador, this.novoColaborador).subscribe({
        next: () => {
          this.isSalvandoColaborador = false;
          this.closeColaboradorModal();
          this.carregarColaboradores();
          this.carregarColaboradoresGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoColaborador = false; }
      });
    }
  }

  confirmarExclusaoColaborador(id: number) {
    this.openConfirmModal('Excluir Colaborador', 'Tem certeza que deseja excluir este colaborador? Esta ação não pode ser desfeita.', () => {
      this.colaboradoresService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarColaboradores();
          this.carregarColaboradoresGeral();
        },
        error: (err) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }

  // ==========================================
  // CATEGORIAS
  // ==========================================
  searchCategoria = '';
  currentCategoriaPage = 1;
  itemsCategoriaPerPage = 10;
  totalCategorias = 0;
  totalCategoriaPages = 1;
  listaCategorias: Categoria[] = [];

  categoriaModalMode: 'create' | 'edit' = 'create';
  isCategoriaModalOpen = false;
  novaCategoria: any = { nome: '', descricao: '' };
  isSalvandoCategoria = false;

  carregarCategorias() {
    this.categoriasService.listar(this.currentCategoriaPage, this.itemsCategoriaPerPage, this.searchCategoria).subscribe({
      next: (res) => {
        this.listaCategorias = res.items;
        this.totalCategorias = res.total;
        this.totalCategoriaPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar categorias', err)
    });
  }

  onSearchCategoriaChange(term: string) {
    this.searchCategoria = term;
    this.currentCategoriaPage = 1;
    this.carregarCategorias();
  }

  goToCategoriaPage(page: number) {
    if (page >= 1 && page <= this.totalCategoriaPages) {
      this.currentCategoriaPage = page;
      this.carregarCategorias();
    }
  }

  openCategoriaModal(categoria?: Categoria) {
    if (categoria) {
      this.categoriaModalMode = 'edit';
      this.novaCategoria = { ...categoria };
    } else {
      this.categoriaModalMode = 'create';
      this.novaCategoria = { nome: '', descricao: '' };
    }
    this.isCategoriaModalOpen = true;
  }

  closeCategoriaModal() {
    this.isCategoriaModalOpen = false;
  }

  salvarCategoria() {
    this.isSalvandoCategoria = true;
    if (this.categoriaModalMode === 'create') {
      this.categoriasService.criar(this.novaCategoria).subscribe({
        next: () => {
          this.isSalvandoCategoria = false;
          this.closeCategoriaModal();
          this.carregarCategorias();
          this.carregarCategoriasGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoCategoria = false; }
      });
    } else {
      this.categoriasService.atualizar(this.novaCategoria.idCategorias, this.novaCategoria).subscribe({
        next: () => {
          this.isSalvandoCategoria = false;
          this.closeCategoriaModal();
          this.carregarCategorias();
          this.carregarCategoriasGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoCategoria = false; }
      });
    }
  }

  confirmarExclusaoCategoria(id: number) {
    this.openConfirmModal('Excluir Categoria', 'Tem certeza que deseja excluir esta categoria? Esta ação não pode ser desfeita.', () => {
      this.categoriasService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarCategorias();
          this.carregarCategoriasGeral();
        },
        error: (err) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }

  // ==========================================
  // CENTROS DE CUSTO
  // ==========================================
  searchCentroCusto = '';
  currentCentroCustoPage = 1;
  itemsCentroCustoPerPage = 10;
  totalCentrosCusto = 0;
  totalCentroCustoPages = 1;
  listaCentrosCusto: CentroCusto[] = [];
  listaCentrosCustoGeral: CentroCusto[] = []; // Para popular selects

  centroCustoModalMode: 'create' | 'edit' = 'create';
  isCentroCustoModalOpen = false;
  novoCentroCusto: any = { codigo: null, nome: '', estados: [] };
  isSalvandoCentroCusto = false;

  estadosBrasil = [
    'Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará', 'Distrito Federal', 'Espírito Santo',
    'Goiás', 'Maranhão', 'Mato Grosso', 'Mato Grosso do Sul', 'Minas Gerais', 'Pará', 'Paraíba',
    'Paraná', 'Pernambuco', 'Piauí', 'Rio de Janeiro', 'Rio Grande do Norte', 'Rio Grande do Sul',
    'Rondônia', 'Roraima', 'Santa Catarina', 'São Paulo', 'Sergipe', 'Tocantins'
  ];

  carregarCentrosCusto() {
    this.centrosCustoService.listar(this.currentCentroCustoPage, this.itemsCentroCustoPerPage, this.searchCentroCusto).subscribe({
      next: (res) => {
        this.listaCentrosCusto = res.items;
        this.totalCentrosCusto = res.total;
        this.totalCentroCustoPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar centros de custo', err)
    });
  }

  onSearchCentroCustoChange(term: string) {
    this.searchCentroCusto = term;
    this.currentCentroCustoPage = 1;
    this.carregarCentrosCusto();
  }

  carregarCentrosCustoGeral() {
    this.centrosCustoService.listar(1, 1000).subscribe({
      next: (res) => {
        this.listaCentrosCustoGeral = (res.items || []).sort((a, b) => a.codigo - b.codigo);
      }
    });
  }

  goToCentroCustoPage(page: number) {
    if (page >= 1 && page <= this.totalCentroCustoPages) {
      this.currentCentroCustoPage = page;
      this.carregarCentrosCusto();
    }
  }

  openCentroCustoModal(centro?: CentroCusto) {
    if (centro) {
      this.centroCustoModalMode = 'edit';
      this.novoCentroCusto = { ...centro, estados: [...(centro.estados || [])] };
    } else {
      this.centroCustoModalMode = 'create';
      this.novoCentroCusto = { codigo: null, nome: '', estados: [] };
    }
    this.isCentroCustoModalOpen = true;
  }

  closeCentroCustoModal() {
    this.isCentroCustoModalOpen = false;
    this.importCcTargetRow = null;
  }

  toggleEstado(estado: string) {
    const index = this.novoCentroCusto.estados.indexOf(estado);
    if (index > -1) {
      this.novoCentroCusto.estados.splice(index, 1);
    } else {
      this.novoCentroCusto.estados.push(estado);
    }
  }

  salvarCentroCusto() {
    this.isSalvandoCentroCusto = true;
    if (this.centroCustoModalMode === 'create') {
      this.centrosCustoService.criar(this.novoCentroCusto).subscribe({
        next: (criado) => {
          this.isSalvandoCentroCusto = false;
          if (this.importCcTargetRow) {
            this.importCcTargetRow.idCentroCusto = criado.idCentroCusto ?? null;
            this.importCcTargetRow.centroCustoNome = criado.nome ?? null;
            this.importCcTargetRow.centroCustoCodigo = criado.codigo;
            this.importCcTargetRow.ccEncontrado = true;
          }
          this.closeCentroCustoModal();
          this.carregarCentrosCusto();
          this.carregarCentrosCustoGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoCentroCusto = false; }
      });
    } else {
      this.centrosCustoService.atualizar(this.novoCentroCusto.idCentroCusto, this.novoCentroCusto).subscribe({
        next: () => {
          this.isSalvandoCentroCusto = false;
          this.closeCentroCustoModal();
          this.carregarCentrosCusto();
          this.carregarCentrosCustoGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoCentroCusto = false; }
      });
    }
  }

  confirmarExclusaoCentroCusto(id: number) {
    this.openConfirmModal('Excluir Centro de Custo', 'Tem certeza que deseja excluir este Centro de Custo? Isso afetará colaboradores vinculados.', () => {
      this.centrosCustoService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarCentrosCusto();
          this.carregarCentrosCustoGeral();
        },
        error: (err: any) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }

  // ==========================================
  // ==========================================
  
  // OUTROS / MOCKS ANTIGOS E EMPRESAS DA API
  // ==========================================
  empresas: Empresa[] = [];

  // Variáveis para a aba de Configuração de Empresas
  searchEmpresaConfig = '';
  currentEmpresaConfigPage = 1;
  itemsEmpresaConfigPerPage = 10;
  totalEmpresasConfig = 0;
  totalEmpresaConfigPages = 1;
  listaEmpresasConfig: Empresa[] = [];

  empresaModalMode: 'create' | 'edit' = 'create';
  isEmpresaModalOpen = false;
  novaEmpresa: any = { nome: '', descricao: '' };
  isSalvandoEmpresa = false;

  carregarEmpresasConfig() {
    this.empresasService.listar(this.currentEmpresaConfigPage, this.itemsEmpresaConfigPerPage, this.searchEmpresaConfig).subscribe({
      next: (res) => {
        this.listaEmpresasConfig = res.items;
        this.totalEmpresasConfig = res.total;
        this.totalEmpresaConfigPages = res.total_pages;
      },
      error: (err) => console.error('Erro ao carregar empresas para config', err)
    });
  }

  onSearchEmpresaConfigChange(term: string) {
    this.searchEmpresaConfig = term;
    this.currentEmpresaConfigPage = 1;
    this.carregarEmpresasConfig();
  }

  goToEmpresaConfigPage(page: number) {
    if (page >= 1 && page <= this.totalEmpresaConfigPages) {
      this.currentEmpresaConfigPage = page;
      this.carregarEmpresasConfig();
    }
  }

  openEmpresaModal(empresa?: Empresa) {
    if (empresa) {
      this.empresaModalMode = 'edit';
      this.novaEmpresa = { ...empresa };
    } else {
      this.empresaModalMode = 'create';
      this.novaEmpresa = { nome: '', descricao: '', modulo_ids: [] };
    }
    this.isEmpresaModalOpen = true;
  }

  closeEmpresaModal() {
    this.isEmpresaModalOpen = false;
  }

  salvarEmpresa() {
    this.isSalvandoEmpresa = true;
    if (this.empresaModalMode === 'create') {
      this.empresasService.criar(this.novaEmpresa).subscribe({
        next: () => {
          this.isSalvandoEmpresa = false;
          this.closeEmpresaModal();
          this.carregarEmpresasConfig();
          
          this.carregarEmpresasGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoEmpresa = false; }
      });
    } else {
      this.empresasService.atualizar(this.novaEmpresa.idEmpresas, this.novaEmpresa).subscribe({
        next: () => {
          this.isSalvandoEmpresa = false;
          this.closeEmpresaModal();
          this.carregarEmpresasConfig();
          
          this.carregarEmpresasGeral();
        },
        error: (err) => { console.error(err); this.isSalvandoEmpresa = false; }
      });
    }
  }

  confirmarExclusaoEmpresa(id: number) {
    this.openConfirmModal('Excluir Empresa', 'Tem certeza que deseja excluir esta Empresa (fatura/extrato)?', () => {
      this.empresasService.excluir(id).subscribe({
        next: () => {
          this.closeConfirmModal();
          this.carregarEmpresasConfig();
          
          this.carregarEmpresasGeral();
        },
        error: (err) => {
          console.error(err);
          this.isConfirmLoading = false;
        }
      });
    });
  }




  isImportColabModalOpen = false;
  importColabState: 'idle' | 'loading' | 'review' | 'processing' | 'done' | 'error' = 'idle';
  importColabError = '';
  importPreview: ImportPreviewResponse | null = null;
  importResumo: ImportProcessarResponse | null = null;
  importCcTargetRow: (ImportNovo | ImportDivergente) | null = null;
  importSearchTerm = '';
  importMostrarDivergenciaOnly = false;

  @ViewChild('colabFileInput') colabFileInput!: ElementRef<HTMLInputElement>;

  openImportColabModal() {
    this.isImportColabModalOpen = true;
    this.importColabState = 'idle';
    this.importColabError = '';
    this.importPreview = null;
    this.importResumo = null;
    this.importSearchTerm = '';
    this.importMostrarDivergenciaOnly = false;
    if (this.colabFileInput?.nativeElement) {
      this.colabFileInput.nativeElement.value = '';
    }
  }

  closeImportColabModal() {
    this.isImportColabModalOpen = false;
  }

  onColabFileChange(event: any) {
    if (event.target.files && event.target.files.length > 0) {
      this.enviarArquivoImportacaoColab(event.target.files[0]);
    }
  }

  enviarArquivoImportacaoColab(file: File) {
    this.importColabState = 'loading';
    this.importColabError = '';

    this.colaboradoresService.importarPreview(file).subscribe({
      next: (res) => {
        this.importPreview = res;
        this.importSearchTerm = '';
        this.importMostrarDivergenciaOnly = false;
        this.importColabState = 'review';
      },
      error: (err) => {
        console.error(err);
        this.importColabState = 'error';
        this.importColabError = err?.error?.detail || 'Erro ao processar a planilha.';
      }
    });
  }

  get importColabPodePrecessar(): boolean {
    if (!this.importPreview) return false;
    const totalLinhas = this.importPreview.novos.length + this.importPreview.divergentes.length + this.importPreview.desligados.length;
    if (totalLinhas === 0) return false;
    return this.importPreview.novos.every(n => !!n.idCentroCusto)
      && this.importPreview.divergentes.every(d => !!d.idCentroCusto);
  }

  private matchesImportSearch(...valores: (string | number | null | undefined)[]): boolean {
    const termo = this.importSearchTerm.trim().toLowerCase();
    if (!termo) return true;
    return valores.some(v => v !== null && v !== undefined && String(v).toLowerCase().includes(termo));
  }

  get importNovosBase(): ImportNovo[] {
    if (!this.importPreview) return [];
    return this.importMostrarDivergenciaOnly
      ? this.importPreview.novos.filter(n => !n.ccEncontrado)
      : this.importPreview.novos;
  }

  get importNovosFiltrados(): ImportNovo[] {
    return this.importNovosBase.filter(n => this.matchesImportSearch(
      n.nome, n.documento, n.centroCustoCodigo, n.centroCustoNome,
      ...n.unidades.map(u => u.codigo), ...n.unidades.map(u => u.descricao)
    ));
  }

  get importDivergentesFiltrados(): ImportDivergente[] {
    if (!this.importPreview) return [];
    return this.importPreview.divergentes.filter(d => this.matchesImportSearch(
      d.nome, d.documento, d.centroCustoCodigo, d.centroCustoNome, d.centroCustoAtualNome,
      ...d.unidades.map(u => u.codigo), ...d.unidadesAtuais.map(u => u.codigo)
    ));
  }

  get importDesligadosFiltrados(): ImportDesligado[] {
    if (!this.importPreview) return [];
    return this.importPreview.desligados.filter(d => this.matchesImportSearch(
      d.nome, d.documento, d.centroCustoAtualNome, ...d.unidadesAtuais.map(u => u.codigo)
    ));
  }

  onCcExistenteSelecionado(linha: ImportNovo | ImportDivergente, cc: CentroCusto | null) {
    linha.idCentroCusto = cc?.idCentroCusto ?? null;
    linha.centroCustoNome = cc?.nome ?? null;
    linha.ccEncontrado = !!cc;
    if (cc) {
      linha.centroCustoCodigo = cc.codigo;
    }
  }

  ccSearchFn(term: string, item: CentroCusto): boolean {
    const termo = term.toLowerCase();
    return String(item.codigo).includes(termo) || (item.nome || '').toLowerCase().includes(termo);
  }

  abrirNovoCcParaImportLinha(linha: ImportNovo | ImportDivergente) {
    this.importCcTargetRow = linha;
    this.novoCentroCusto = { codigo: linha.centroCustoCodigo, nome: '', estados: [] };
    this.centroCustoModalMode = 'create';
    this.isCentroCustoModalOpen = true;
  }

  processarImportacaoColab() {
    if (!this.importPreview || !this.importColabPodePrecessar) return;
    this.importColabState = 'processing';

    const payload = {
      novos: this.importPreview.novos.map(n => ({
        documento: n.documento,
        nome: n.nome,
        idCentroCusto: n.idCentroCusto as number,
        unidadeIds: n.unidades.map(u => u.idUnidade)
      })),
      divergentes: this.importPreview.divergentes.map(d => ({
        idColaborador: d.idColaborador,
        idCentroCusto: d.idCentroCusto as number,
        unidadeIds: d.unidades.map(u => u.idUnidade)
      })),
      desligados: this.importPreview.desligados.map(d => ({ idColaborador: d.idColaborador }))
    };

    this.colaboradoresService.importarProcessar(payload).subscribe({
      next: (res) => {
        this.importResumo = res;
        this.importColabState = 'done';
        this.carregarColaboradores();
        this.carregarColaboradoresGeral();
      },
      error: (err) => {
        console.error(err);
        this.importColabState = 'error';
        this.importColabError = err?.error?.detail || 'Erro ao processar a importação.';
      }
    });
  }

}
