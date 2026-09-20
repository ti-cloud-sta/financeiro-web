with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

header_and_visao_geral = ''.join(lines[:166])

financeiro_real = """
                <div *ngIf="dashboardTab() === 'financeiro'">
                  <div class="dash-kpi-panel p-3 mb-4 border rounded-3 bg-white">
                    <div class="row g-4 mb-4">
                      <div class="col-12">
                        <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">
                          <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0 fw-semibold text-secondary">
                              Títulos Financeiros
                              <span class="badge bg-light text-secondary ms-2 border fw-normal">{{ gridFinanceiro.length }}</span>
                            </h6>
                            <div class="config-toolbar mb-0">
                              <div class="search-box">
                                <i class="fa-solid fa-search text-muted position-absolute" style="left: 10px; top: 50%; transform: translateY(-50%);"></i>
                                <input type="text" class="form-control form-control-sm" placeholder="Buscar..."
                                  [(ngModel)]="searchFinanceiro" (ngModelChange)="pageFinanceiro = 1" style="padding-left: 28px;">
                              </div>
                            </div>
                          </div>
                          <table class="saas-table w-100 mt-2">
                            <thead>
                              <tr>
                                <th>Título</th>
                                <th>Cliente</th>
                                <th>Fase</th>
                                <th>Vencimento</th>
                                <th>Status</th>
                                <th class="text-center">Atraso</th>
                                <th class="text-end">Valor</th>
                                <th class="text-center">Tratativas/Histórico</th>
                              </tr>
                            </thead>
                            <tbody>
"""

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html.backup', 'r', encoding='utf-8') as f:
    backup_lines = f.readlines()

logistica_start_idx = 0
pendencias_start_idx = len(backup_lines)

for i, line in enumerate(backup_lines):
    if '<!-- Tab Logística -->' in line:
        logistica_start_idx = i
    if '<!-- Tab Pendências -->' in line:
        pendencias_start_idx = i
        break

financeiro_end = ''.join(backup_lines[:logistica_start_idx])

logistica_and_comercial = ''.join(backup_lines[logistica_start_idx:pendencias_start_idx])
logistica_and_comercial = logistica_and_comercial.replace(
    '<div class="tab-pane fade" [class.show]="activeTab === \'logistica\'" [class.active]="activeTab === \'logistica\'" role="tabpanel">',
    '<div *ngIf="dashboardTab() === \'logistica\'">'
)
logistica_and_comercial = logistica_and_comercial.replace(
    '<div class="tab-pane fade" [class.show]="activeTab === \'comercial\'" [class.active]="activeTab === \'comercial\'" role="tabpanel">',
    '<div *ngIf="dashboardTab() === \'comercial\'">'
)

layout_endings = """
              </div> <!-- END panel-container -->
            </main>
          </div>
        </div>

"""

pendencias_and_modals = ''.join(lines[310:])

final_html = (
    header_and_visao_geral +
    financeiro_real +
    financeiro_end +
    logistica_and_comercial +
    layout_endings +
    pendencias_and_modals
)

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print("HTML Reconstructed Successfully!")
