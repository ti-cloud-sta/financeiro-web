import json
with open(r'C:\Users\JOE\.gemini\antigravity-ide\brain\1f74a8e4-d1bd-4bad-abef-3f1d0b9fd760\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'content' in data and type(data['content']) == str:
                if 'dashboardTab() === \'visao-geral\'' in data['content'] and '<!-- SKELETON: FINANCEIRO -->' in data['content']:
                    with open('visao_geral_transcript.txt', 'a', encoding='utf-8') as out:
                        out.write(data['content'])
                        out.write('\n----------------------------------------\n')
        except Exception as e:
            pass
