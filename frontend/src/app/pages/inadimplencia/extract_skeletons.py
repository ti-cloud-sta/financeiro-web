import re

file_path = r'c:\Users\JOE\Documents\GitHub\financeiro-web\frontend\src\app\pages\inadimplencia\inadimplencia.component.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(<div \*ngIf="isDashboardLoading\(\)">.*?<!-- CONTEUDO REAL -->)', content, flags=re.DOTALL)
if m:
    with open('skeleton_block.html', 'w', encoding='utf-8') as f:
        f.write(m.group(1))
    print(f'Skeleton block saved to skeleton_block.html (Length: {len(m.group(1))})')
else:
    print('Skeleton block not found')
