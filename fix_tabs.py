import re

path = 'frontend/src/app/pages/inadimplencia/inadimplencia.component.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the invalid top-level tabs that were added previously
# The Logistica tab starts at <!-- Tab Logística --> and ends at <!-- Tab Comercial -->
# The Comercial tab starts at <!-- Tab Comercial --> and ends at <!-- Tab Pendências -->

# First let's extract the actual panel-container contents from inside the rogue tabs
# Logistica panel-container content
logistica_match = re.search(r'<!-- Tab Logística -->.*?<div class="panel-container">(.*?)</div>\s*</div>\s*</div>\s*</div>\s*<!-- Tab Comercial -->', content, re.DOTALL)
logistica_content = logistica_match.group(1) if logistica_match else ""

comercial_match = re.search(r'<!-- Tab Comercial -->.*?<div class="panel-container">(.*?)</div>\s*</div>\s*</div>\s*</div>\s*<!-- Tab Pendências -->', content, re.DOTALL)
comercial_content = comercial_match.group(1) if comercial_match else ""

print("Extracted Logistica length:", len(logistica_content))
print("Extracted Comercial length:", len(comercial_content))

# If we couldn't extract them, we have a bigger problem
if not logistica_content or not comercial_content:
    print("Could not extract tab contents!")
    import sys
    sys.exit(1)

# Now, we need to locate the end of the Financeiro grid
# and then insert the proper <div *ngIf="dashboardTab() === 'logistica'"> and comercial wrappers

# Let's locate the stray "Maiores Acordos Comerciais" part which shouldn't be there
stray_acordos_pattern = r'<div class="row g-4 mb-4 align-items-stretch">.*?<h6 class="mb-3 fw-semibold text-secondary">Maiores Acordos Comerciais</h6>.*?</div>\s*</div>\s*</div>'
stray_acordos_match = re.search(stray_acordos_pattern, content, re.DOTALL)
stray_acordos_content = stray_acordos_match.group(0) if stray_acordos_match else ""
print("Extracted stray acordos length:", len(stray_acordos_content))

# Now remove the stray acordos content from its current position
new_content = content.replace(stray_acordos_content, "")

# Remove the rogue top-level tabs completely
rogue_tabs_pattern = r'<!-- Tab Logística -->.*?<!-- Tab Pendências -->'
new_content = re.sub(rogue_tabs_pattern, '<!-- Tab Pendências -->', new_content, flags=re.DOTALL)

# Reconstruct the Comercial tab content combining the stray acordos with the extracted comercial grid
proper_comercial_content = f"""
                  <!-- Stray Acordos Comerciais that was outside -->
                  {stray_acordos_content}
                  
                  <!-- Grid Acordos Comerciais -->
                  {comercial_content}
"""

# Reconstruct the Logistica wrapper
proper_logistica_html = f"""
                <div *ngIf="dashboardTab() === 'logistica'">
                  {logistica_content}
                </div>
"""

proper_comercial_html = f"""
                <div *ngIf="dashboardTab() === 'comercial'">
                  {proper_comercial_content}
                </div>
"""

# Insert these proper wrappers right after the end of the Financeiro wrapper
financeiro_end_pattern = r'(</div>\s*<!-- Fim grid financeiro -->\s*</div>\s*</div>\s*</div>)'
replacement = r'\1' + '\n' + proper_logistica_html + '\n' + proper_comercial_html
new_content = re.sub(financeiro_end_pattern, replacement, new_content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("HTML structure fixed successfully.")
