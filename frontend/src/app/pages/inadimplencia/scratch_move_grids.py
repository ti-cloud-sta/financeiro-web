import sys
import re

file_path = r'c:\Users\JOE\Documents\GitHub\financeiro-web\frontend\src\app\pages\inadimplencia\inadimplencia.component.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The grid block starts right before the Títulos Sem Entrega card.
# The previous sibling is the Charts row.
# Let's find the Exact strings.

# Target insertion point: Inside the "Atual" panel, after the `<div class="row g-4">` closes.
# Wait, let's just find the closing `</div>` of the "Atual" panel.
# The "Atual" panel has `<h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>`

atual_match = re.search(r'(<h5 class="fw-bold text-secondary mb-0 ms-1">Atual</h5>.*?)      </div>\n\n      <div class="row g-4 mb-4">', content, flags=re.DOTALL)

if not atual_match:
    print("Could not find Atual panel")
    sys.exit(1)

# Now find the grids block.
# The grids block is the row that contains "Títulos Sem Entrega"
grid_block_start = content.find('      <div class="row g-4 mb-4">\n        <div class="col-12 col-xl-6">\n          <div class="dash-chart-card p-3 bg-white border rounded-3 shadow-sm h-100">\n            <div class="d-flex justify-content-between align-items-center mb-3">\n              <h6 class="mb-0 fw-semibold text-secondary">Títulos Sem Entrega</h6>')

if grid_block_start == -1:
    print("Could not find grid block start")
    sys.exit(1)

# Find the end of this row. It ends right before `    </div>\n\n    <!-- DASHBOARD: COMERCIAL -->`
grid_block_end = content.find('    </div>\n\n    <!-- DASHBOARD: COMERCIAL -->')

if grid_block_end == -1:
    print("Could not find grid block end")
    sys.exit(1)

grid_block_end = content.rfind('      </div>\n', 0, grid_block_end) + len('      </div>\n')

grids_content = content[grid_block_start:grid_block_end]

# Remove the grids from the original position
content = content[:grid_block_start] + content[grid_block_end:]

# Now insert the grids inside the Atual panel
# The Atual panel ends right before the next `<div class="row g-4 mb-4">` (which are the Total cards)
# We found it earlier:
insertion_idx = content.find('      </div>\n\n      <div class="row g-4 mb-4">', atual_match.start())
if insertion_idx == -1:
    print("Could not find insertion point")
    sys.exit(1)

# Insert the grids right before the closing </div> of the Atual panel, inside a <div class="mt-4"> maybe?
# The user wants "grids logo dentro do card Atual". So let's wrap it slightly if needed, or just insert it.
grids_to_insert = '\n        <div class="mt-4 border-top pt-4">\n' + grids_content.replace('      <div', '          <div').replace('      </div>', '          </div>') + '\n        </div>\n'

content = content[:insertion_idx] + grids_to_insert + content[insertion_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Grids moved successfully!")
