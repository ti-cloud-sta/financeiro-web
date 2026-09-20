import sys
import re

file_path = r'c:\Users\JOE\Documents\GitHub\financeiro-web\frontend\src\app\pages\inadimplencia\inadimplencia.component.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Target insertion point: Inside the "Atual" panel of FINANCEIRO, right before its closing `</div>`
# The Financeiro Atual panel starts with `<h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>` 
# and is the first one under `<!-- DASHBOARD: FINANCEIRO (GERENCIAL) -->`
# Wait, let's search specifically for the financeiro block

financeiro_block_match = re.search(r'<!-- DASHBOARD: FINANCEIRO \(GERENCIAL\) -->(.*?)<!-- DASHBOARD: LOGISTICA -->', content, flags=re.DOTALL)
if not financeiro_block_match:
    print("Could not find Financeiro block")
    sys.exit(1)

financeiro_block = financeiro_block_match.group(1)

# Inside financeiro_block, we have the Atual panel
atual_match = re.search(r'(<h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>.*?)      </div>\n\n      <div class="row g-4 mb-4">\n        <div class="col-12">\n          <div class="dash-chart-card', financeiro_block, flags=re.DOTALL)

if not atual_match:
    print("Could not find Atual panel inside Financeiro")
    sys.exit(1)

# Grid block start:
grid_block_start = financeiro_block.find('      <div class="row g-4 mb-4">\n        <div class="col-12">\n          <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm">\n            <div class="d-flex justify-content-between align-items-center mb-3">\n              <h6 class="mb-0 fw-semibold text-secondary">Títulos com Maiores Valores em Atraso</h6>')

if grid_block_start == -1:
    print("Could not find grid block start in Financeiro")
    sys.exit(1)

# Grid block end
# The grid block ends right before the Charts block, which starts with:
# `      <div class="row g-4 mb-4">\n        <div class="col-12 col-xl-8">\n          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">\n            <h6 class="mb-3 fw-semibold text-secondary">Títulos Pagos Fora do Prazo (Anual)</h6>`
grid_block_end = financeiro_block.find('      <div class="row g-4 mb-4">\n        <div class="col-12 col-xl-8">\n          <div class="dash-chart-card h-100 p-3 bg-white border rounded-3 shadow-sm">\n            <h6 class="mb-3 fw-semibold text-secondary">Títulos Pagos Fora do Prazo (Anual)</h6>')

if grid_block_end == -1:
    print("Could not find grid block end in Financeiro")
    sys.exit(1)

grid_block_end = financeiro_block.rfind('      </div>\n\n', 0, grid_block_end) + len('      </div>\n')

grids_content = financeiro_block[grid_block_start:grid_block_end]

# Remove the grids from original pos
new_financeiro_block = financeiro_block[:grid_block_start] + financeiro_block[grid_block_end:]

# Find insertion point (the closing `</div>` of the Atual panel)
# In the new_financeiro_block, it's right before the Charts block, because the grids were in between.
# Wait, actually, let's just find the closing </div> of the Atual panel.
# We know it ends exactly at `grid_block_start`, because the grids immediately followed it.
# So in new_financeiro_block, the Atual panel's closing `      </div>` is right before `new_financeiro_block`'s `grid_block_start` index.
insertion_idx = new_financeiro_block.rfind('      </div>', 0, grid_block_start)

if insertion_idx == -1:
    print("Could not find insertion point")
    sys.exit(1)

grids_to_insert = '\n        <div class="mt-4 border-top pt-4">\n' + grids_content.replace('      <div', '          <div').replace('      </div>', '          </div>').replace('      </nav>', '          </nav>').replace('      </table>', '          </table>') + '        </div>\n'

new_financeiro_block = new_financeiro_block[:insertion_idx] + grids_to_insert + new_financeiro_block[insertion_idx:]

content = content[:financeiro_block_match.start(1)] + new_financeiro_block + content[financeiro_block_match.end(1):]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Grids moved successfully for Financeiro!")
