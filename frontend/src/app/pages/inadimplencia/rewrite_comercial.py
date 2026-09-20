import sys
import re

file_path = r'c:\Users\JOE\Documents\GitHub\financeiro-web\frontend\src\app\pages\inadimplencia\inadimplencia.component.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the entire Comercial block
comercial_match = re.search(r'(<!-- DASHBOARD: COMERCIAL -->.*?</div>\n    </div>)\n\n  </div>', content, flags=re.DOTALL)
if not comercial_match:
    print("Could not find Comercial block")
    sys.exit(1)

comercial_block = comercial_match.group(1)

# I need to extract pieces from it:
# 1. Total Card
total_card_m = re.search(r'(<div class="dash-chart-card p-4 bg-white border rounded-3 shadow-sm d-flex flex-column align-items-center justify-content-center h-100">.*?</div>)', comercial_block, flags=re.DOTALL)
total_card = total_card_m.group(1)

# 2. Ranking Grid
ranking_grid_m = re.search(r'(<div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">\s*<h6 class="mb-3 fw-semibold text-secondary">Maiores Acordos Comerciais</h6>.*?</div>)', comercial_block, flags=re.DOTALL)
ranking_grid = ranking_grid_m.group(1)

# 3. Chart
chart_m = re.search(r'(<div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm d-flex flex-column">.*?</div>)', comercial_block, flags=re.DOTALL)
chart = chart_m.group(1)

# 4. Main Grid
main_grid_m = re.search(r'(<div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">\s*<div class="d-flex justify-content-between align-items-center mb-3">\s*<h6 class="mb-0 fw-semibold text-secondary">Títulos em Acordo Comercial</h6>.*?</div>\n        </div>)', comercial_block, flags=re.DOTALL)
main_grid = main_grid_m.group(1)

# Wait, the main_grid matches until the end of the col-12.
# Let's adjust main_grid to only capture the content of `dash-chart-card`
main_grid_m2 = re.search(r'(<div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">\s*<div class="d-flex justify-content-between align-items-center mb-3">\s*<h6 class="mb-0 fw-semibold text-secondary">Títulos em Acordo Comercial</h6>.*?</nav>\n          </div>)', comercial_block, flags=re.DOTALL)

# Because there might be an ngIf on the nav, let's use a safer extract.
# `main_grid` from `<div class="dash-chart-card...>` to the closing of that card.
# The original structure:
"""
        <div class="col-12">
          <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">
            ...
            <nav ...>
              ...
            </nav>
          </div>
        </div>
"""
main_grid_idx1 = comercial_block.find('<div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">\n            <div class="d-flex justify-content-between align-items-center mb-3">\n              <h6 class="mb-0 fw-semibold text-secondary">Títulos em Acordo Comercial</h6>')
main_grid_idx2 = comercial_block.find('          </div>\n        </div>\n      </div>\n    </div>')
main_grid = comercial_block[main_grid_idx1:main_grid_idx2]

# Also let's fix Total Card height to not have `h-100` if it's sitting alone.
total_card = total_card.replace(' h-100"', '"')

new_comercial_block = f"""<!-- DASHBOARD: COMERCIAL -->
    <div *ngIf="dashboardTab() === 'comercial'">
      
      <!-- Painel: Atual -->
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>
        <div class="d-flex align-items-center ms-1 mb-4">
          <span class="badge bg-light text-secondary border fw-normal px-2 py-1">
            <i class="fa-regular fa-calendar me-2"></i>{{{{ dataHoje | date:'dd/MM/yyyy' }}}}
          </span>
        </div>

        <div class="row g-4">
          <div class="col-12 col-md-6 col-xl-4">
            {total_card.replace('            ', '            ')}
          </div>
        </div>

        <div class="row g-4 mt-4 pt-4 border-top">
          <div class="col-12">
            {main_grid.replace('            <div class', '            <div class')}
          </div>
        </div>
      </div>

      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-4">
          {ranking_grid.replace('                <div class', '            <div class')}
        </div>
        <div class="col-12 col-xl-8">
          {chart.replace('            <div class', '            <div class')}
        </div>
      </div>
    </div>"""

# Remove extra indent from the variables to fix formatting
total_card = total_card.strip()
ranking_grid = ranking_grid.strip()
chart = chart.strip()
main_grid = main_grid.strip()

# Better formatting approach:
new_comercial_block = f"""<!-- DASHBOARD: COMERCIAL -->
    <div *ngIf="dashboardTab() === 'comercial'">
      
      <!-- Painel: Atual -->
      <div class="dash-kpi-panel border rounded-4 p-4 mb-4 border-2">
        <h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>
        <div class="d-flex align-items-center ms-1 mb-4">
          <span class="badge bg-light text-secondary border fw-normal px-2 py-1">
            <i class="fa-regular fa-calendar me-2"></i>{{{{ dataHoje | date:'dd/MM/yyyy' }}}}
          </span>
        </div>

        <div class="row g-4">
          <div class="col-12 col-md-6 col-xl-4">
            {total_card}
          </div>
        </div>

        <div class="row g-4 mt-4 pt-4 border-top">
          <div class="col-12">
            {main_grid}
          </div>
        </div>
      </div>

      <div class="row g-4 mb-4">
        <div class="col-12 col-xl-4 h-100">
          {ranking_grid}
        </div>
        <div class="col-12 col-xl-8 h-100">
          {chart}
        </div>
      </div>
    </div>"""

content = content[:comercial_match.start()] + new_comercial_block + content[comercial_match.end():]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Comercial block restructured successfully!")
