import re

with open('header_and_visao_geral.txt', 'r', encoding='utf-8') as f:
    header = f.read()

with open('rebuild_html_fixed.py', 'r', encoding='utf-8') as f:
    rebuild_code = f.read()

import ast
tree = ast.parse(rebuild_code)
financeiro_real = ''
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        if getattr(node.targets[0], 'id', '') == 'financeiro_real':
            financeiro_real = node.value.value
            break

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html.backup', 'r', encoding='utf-8') as f:
    backup_lines = f.readlines()

logistica_start_idx = 0
pendencias_start_idx = len(backup_lines)

for i, line in enumerate(backup_lines):
    if '<!-- Tab Log' in line:
        logistica_start_idx = i
    if '<!-- Tab Pend' in line:
        pendencias_start_idx = i
        break

financeiro_end = ''.join(backup_lines[:logistica_start_idx])

# Fix logistica
logistica_lines = backup_lines[logistica_start_idx:pendencias_start_idx]
logistica_text = ''.join(logistica_lines)

logistica_text = re.sub(
    r'<div class="tab-pane fade".*?>\s*<div class="config-layout">\s*<div class="dashboard-header border-bottom">\s*<h3 class="mb-0 p-3".*?>Log.*?istica</h3>\s*</div>\s*<div class="panel-container">',
    '<div *ngIf="dashboardTab() === \'logistica\'">',
    logistica_text, flags=re.DOTALL
)

logistica_text = re.sub(
    r'<div class="tab-pane fade".*?>\s*<div class="config-layout">\s*<div class="dashboard-header border-bottom">\s*<h3 class="mb-0 p-3".*?>Comercial</h3>\s*</div>\s*<div class="panel-container">',
    '<div *ngIf="dashboardTab() === \'comercial\'">',
    logistica_text, flags=re.DOTALL
)

logistica_text = re.sub(r'</div>\s*</div>\s*</div>\s*</div>\s*(?=<!-- Tab Comercial -->)', '</div>\n', logistica_text, flags=re.DOTALL)
logistica_text = re.sub(r'</div>\s*</div>\s*</div>\s*</div>\s*$', '</div>\n', logistica_text, flags=re.DOTALL)

layout_endings = '''
              </div> <!-- END panel-container -->
            </main>
          </div>
        </div>
'''

with open('modal_tratativas.txt', 'r', encoding='utf-8') as f:
    modals_text = f.read()

out_modals = []
start = False
for line in modals_text.split('\n'):
    if '616:           </div>' in line:
        start = True
    if start:
        m = re.match(r'^\d+:\s?(.*)', line)
        if m:
            out_modals.append(m.group(1) + '\n')

final_html = header + financeiro_real + financeiro_end + logistica_text + layout_endings + ''.join(out_modals)

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print('SUCCESS!')
