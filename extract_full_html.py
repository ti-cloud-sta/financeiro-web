import json
import re

first_half = []
second_half = []

with open(r'C:\Users\JOE\.gemini\antigravity-ide\brain\1f74a8e4-d1bd-4bad-abef-3f1d0b9fd760\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'content' in data and type(data['content']) == str:
                content = data['content']
                if 'Total Lines: 1401' in content:
                    if 'Showing lines 1 to 800' in content:
                        first_half.append(content)
                    elif 'Showing lines 800 to 1401' in content or 'ContentOffset' in content or 'Showing lines' in content:
                        second_half.append(content)
        except Exception as e:
            pass

def extract_lines(text):
    out = []
    lines = text.split('\n')
    start_parsing = False
    for line in lines:
        if 'The following code has been modified' in line:
            start_parsing = True
            continue
        if start_parsing:
            if line.strip() == 'The above content shows the entire, complete file contents of the requested file.' or line.strip().startswith('The above content shows a truncated'):
                break
            match = re.match(r'^\d+:\s?(.*)', line)
            if match:
                out.append(match.group(1) + '\n')
    return out

final_lines = []
if first_half:
    final_lines.extend(extract_lines(first_half[-1]))
if second_half:
    final_lines.extend(extract_lines(second_half[-1]))

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print(f'Restored {len(final_lines)} lines!')
