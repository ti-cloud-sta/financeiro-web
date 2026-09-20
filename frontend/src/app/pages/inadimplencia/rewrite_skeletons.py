import sys
import re

file_path = r'c:\Users\JOE\Documents\GitHub\financeiro-web\frontend\src\app\pages\inadimplencia\inadimplencia.component.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(<div \*ngIf="isDashboardLoading\(\)">.*?<!-- CONTEUDO REAL -->)', content, flags=re.DOTALL)
if not m:
    print('Skeleton block not found!')
    sys.exit(1)

new_skeletons = """<div *ngIf="isDashboardLoading()">
    <!-- SKELETON: VISÃO GERAL -->
    <div *ngIf="dashboardTab() === 'visao-geral'">
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-3 ms-1">Financeiro</h5>
        <div class="row g-4">
          <div class="col-12 col-xl-4"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="250px"></app-skeleton></div></div>
          <div class="col-12 col-xl-4"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="250px"></app-skeleton></div></div>
          <div class="col-12 col-xl-4"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="250px"></app-skeleton></div></div>
        </div>
      </div>
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-3 ms-1">Logística</h5>
        <div class="row g-4">
          <div class="col-12 col-xl-6"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="250px"></app-skeleton></div></div>
          <div class="col-12 col-xl-6"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="250px"></app-skeleton></div></div>
        </div>
      </div>
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-3 ms-1">Comercial</h5>
        <div class="row g-4">
          <div class="col-12 col-xl-6"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm"><app-skeleton type="text" width="50%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="280px"></app-skeleton></div></div>
          <div class="col-12 col-xl-6">
            <div class="row g-4">
              <div class="col-12"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm d-flex flex-column align-items-center justify-content-center" style="height: 120px;"><app-skeleton type="text" width="60%" height="14px" class="mb-2"></app-skeleton><app-skeleton type="rect" width="40%" height="32px"></app-skeleton></div></div>
              <div class="col-12"><div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm" style="height: 140px;"><app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton><app-skeleton type="rect" width="100%" height="80px"></app-skeleton></div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SKELETON: FINANCEIRO -->
    <div *ngIf="dashboardTab() === 'financeiro'">
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-3 ms-1">Atual</h5>
        <div class="row g-4">
          <div class="col-12 col-md-6">
            <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column justify-content-center">
               <app-skeleton type="text" width="40%" height="14px" class="mb-2"></app-skeleton>
               <app-skeleton type="rect" width="50%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column justify-content-center">
               <app-skeleton type="text" width="40%" height="14px" class="mb-2"></app-skeleton>
               <app-skeleton type="rect" width="50%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
            </div>
          </div>
        </div>
        <div class="row g-4 mt-4 pt-4 border-top">
          <div class="col-12">
            <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">
              <app-skeleton type="text" width="30%" height="18px" class="mb-3"></app-skeleton>
              <app-skeleton type="rect" width="100%" height="300px"></app-skeleton>
            </div>
          </div>
        </div>
      </div>
      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-8">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton>
            <app-skeleton type="rect" width="100%" height="280px"></app-skeleton>
          </div>
        </div>
        <div class="col-12 col-xl-4">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton>
            <div class="d-flex justify-content-center align-items-center" style="height: 280px;">
              <app-skeleton type="rect" width="220px" height="220px" [style.border-radius]="'50%'"></app-skeleton>
            </div>
          </div>
        </div>
      </div>
      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-4">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="50%" height="18px" class="mb-3"></app-skeleton>
            <app-skeleton type="rect" width="100%" height="280px"></app-skeleton>
          </div>
        </div>
      </div>
    </div>

    <!-- SKELETON: LOGISTICA -->
    <div *ngIf="dashboardTab() === 'logistica'">
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-3 ms-1">Atual</h5>
        <div class="row g-4">
          <div class="col-12 col-md-6">
            <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column justify-content-center">
               <app-skeleton type="text" width="40%" height="14px" class="mb-2"></app-skeleton>
               <app-skeleton type="rect" width="50%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column justify-content-center">
               <app-skeleton type="text" width="40%" height="14px" class="mb-2"></app-skeleton>
               <app-skeleton type="rect" width="50%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
            </div>
          </div>
        </div>
        <div class="mt-4 border-top pt-4">
          <div class="row g-4 mb-4">
            <div class="col-12 col-xl-6">
              <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm h-100">
                <app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton>
                <app-skeleton type="rect" width="100%" height="250px"></app-skeleton>
              </div>
            </div>
            <div class="col-12 col-xl-6">
              <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm h-100">
                <app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton>
                <app-skeleton type="rect" width="100%" height="250px"></app-skeleton>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="row g-4 mb-4">
        <div class="col-12 col-md-6">
          <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column align-items-center justify-content-center">
             <app-skeleton type="text" width="60%" height="14px" class="mb-2"></app-skeleton>
             <app-skeleton type="rect" width="40%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column align-items-center justify-content-center">
             <app-skeleton type="text" width="60%" height="14px" class="mb-2"></app-skeleton>
             <app-skeleton type="rect" width="40%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
          </div>
        </div>
      </div>
      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-6">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton>
            <app-skeleton type="rect" width="100%" height="280px"></app-skeleton>
          </div>
        </div>
        <div class="col-12 col-xl-6">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton>
            <app-skeleton type="rect" width="100%" height="280px"></app-skeleton>
          </div>
        </div>
      </div>
    </div>

    <!-- SKELETON: COMERCIAL -->
    <div *ngIf="dashboardTab() === 'comercial'">
      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-6">
          <div class="row g-4">
            <div class="col-12">
              <div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column align-items-center justify-content-center" style="height: 120px;">
                <app-skeleton type="text" width="40%" height="14px" class="mb-2"></app-skeleton>
                <app-skeleton type="rect" width="30%" height="32px" [style.border-radius]="'8px'"></app-skeleton>
              </div>
            </div>
            <div class="col-12">
              <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">
                <app-skeleton type="text" width="40%" height="18px" class="mb-3"></app-skeleton>
                <app-skeleton type="rect" width="100%" height="175px"></app-skeleton>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 col-xl-6">
          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">
            <app-skeleton type="text" width="60%" height="18px" class="mb-3"></app-skeleton>
            <app-skeleton type="rect" width="100%" height="280px"></app-skeleton>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- CONTEUDO REAL -->"""

content = content[:m.start(1)] + new_skeletons + content[m.end(1):]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Skeletons updated successfully!")
