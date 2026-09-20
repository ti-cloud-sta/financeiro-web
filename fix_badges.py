import re

path = 'frontend/src/app/pages/inadimplencia/inadimplencia.component.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Replace any badge with complex ngClass + statusColor back to simple kanban pattern
# Pattern for t.status (financeiro and logistica grids)
content = re.sub(
    r'<td><span class="badge[^"]*"[\s\S]*?\[ngClass\]="[\s\S]*?t\.statusColor[\s\S]*?">{{ t\.status }}</span></td>',
    '<td><span class="badge status-badge bg-{{t.statusColor}} bg-opacity-10 text-{{t.statusColor}}">{{ t.status }}</span></td>',
    content
)

# Pattern for ga.status (acordos grid)
content = re.sub(
    r'<td><span class="badge[^"]*"[\s\S]*?\[ngClass\]="[\s\S]*?ga\.statusColor[\s\S]*?">{{ ga\.status }}</span></td>',
    '<td><span class="badge status-badge bg-{{ga.statusColor}} bg-opacity-10 text-{{ga.statusColor}}">{{ ga.status }}</span></td>',
    content
)

# Pattern for modal tratativas statusColor
content = re.sub(
    r'<span class="badge[^"]*"[\s\n\r]*style="[^"]*"[\s\n\r]*\[ngClass\]="[\s\S]*?tituloSelecionadoTratativas\.statusColor[\s\S]*?">{{ tituloSelecionadoTratativas\.status }}</span>',
    '<span class="badge status-badge bg-{{tituloSelecionadoTratativas.statusColor}} bg-opacity-10 text-{{tituloSelecionadoTratativas.statusColor}}">{{ tituloSelecionadoTratativas.status }}</span>',
    content
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done! Replacements applied.')
print('Checking remaining ngClass statusColor:')
matches = re.findall(r'ngClass.*?statusColor', content)
print(f'Remaining: {len(matches)}')
