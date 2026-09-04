import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../modal/modal.component';
import { ButtonComponent } from '../button/button.component';
import { CargoModalComponent } from '../cargo-modal/cargo-modal.component';
import { ColaboradoresService } from '../../../core/services/colaboradores.service';
import { CentrosCustoService } from '../../../core/services/centros-custo.service';
import { UnidadesService } from '../../../core/services/unidades.service';
import { CargosColaboradoresService, CargoColaborador } from '../../../core/services/cargos-colaboradores.service';

@Component({
  selector: 'app-colaborador-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, ButtonComponent, CargoModalComponent],
  templateUrl: './colaborador-modal.component.html',
  styleUrls: ['./colaborador-modal.component.scss']
})
export class ColaboradorModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() modalMode: 'create' | 'edit' = 'create';
  @Input() initialName = '';
  @Input() colaboradorData: any = null;
  @Output() closed = new EventEmitter<void>();
  @Output() saved = new EventEmitter<any>();

  colaboradoresService = inject(ColaboradoresService);
  centrosCustoService = inject(CentrosCustoService);
  unidadesService = inject(UnidadesService);
  cargosService = inject(CargosColaboradoresService);

  listaCentrosCusto: any[] = [];
  listaUnidades: any[] = [];
  listaCargos: CargoColaborador[] = [];

  novoColaborador: any = { nome: '', idCentroCusto: null, idCargoColaborador: null, idUnidade: null, papel: '' };
  isSalvando = false;
  isCargoModalOpen = false;

  ngOnInit() {
    this.carregarListas();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['isOpen'] && changes['isOpen'].currentValue === true) {
      this.carregarListas(); // Refresh lists when opened
      if (this.modalMode === 'edit' && this.colaboradorData) {
        this.novoColaborador = {
          ...this.colaboradorData,
          idUnidade: this.colaboradorData.unidades?.[0]?.idUnidade ?? null
        };
      } else {
        this.novoColaborador = { nome: this.initialName || '', idCentroCusto: null, idCargoColaborador: null, idUnidade: null, papel: '' };
      }
    }
  }

  carregarListas() {
    this.centrosCustoService.listar(1, 1000).subscribe({
      next: (res) => this.listaCentrosCusto = (res.items || []).sort((a, b) => a.codigo - b.codigo)
    });
    this.unidadesService.listar(1, 1000).subscribe({
      next: (res) => this.listaUnidades = (res.items || []).sort((a, b) => a.descricao.localeCompare(b.descricao))
    });
    this.carregarCargos();
  }

  carregarCargos() {
    this.cargosService.listar(1, 1000).subscribe({
      next: (res) => this.listaCargos = (res.items || []).sort((a, b) => a.nome.localeCompare(b.nome))
    });
  }

  salvar() {
    this.isSalvando = true;
    const payload = {
      ...this.novoColaborador,
      unidadeIds: this.novoColaborador.idUnidade ? [this.novoColaborador.idUnidade] : []
    };
    if (this.modalMode === 'create') {
      this.colaboradoresService.criar(payload).subscribe({
        next: (salvo) => {
          this.isSalvando = false;
          this.saved.emit(salvo);
          this.fechar();
        },
        error: (err) => {
          console.error(err);
          this.isSalvando = false;
        }
      });
    } else {
      this.colaboradoresService.atualizar(this.novoColaborador.idColaborador, payload).subscribe({
        next: (salvo) => {
          this.isSalvando = false;
          this.saved.emit(salvo);
          this.fechar();
        },
        error: (err) => {
          console.error(err);
          this.isSalvando = false;
        }
      });
    }
  }

  openNovoCargoModal() {
    this.isCargoModalOpen = true;
  }

  onCargoSaved(novoCargo: CargoColaborador) {
    this.carregarCargos();
    this.novoColaborador.idCargoColaborador = novoCargo.idCargoColaborador;
  }

  fechar() {
    this.closed.emit();
  }
}
