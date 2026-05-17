"""Distill research raw into topic-organized prompts."""
import json

data = json.load(open('_research_raw.json', 'r', encoding='utf-8'))

out_lines = []
for topic, items in data.items():
    out_lines.append(f'\n========== TOPIC: {topic} ==========')
    seen_url = set()
    for it in items:
        for r in it.get('results', []):
            u = r.get('url', '')
            if not u or u in seen_url:
                continue
            seen_url.add(u)
            title = r.get('title', '')
            desc = r.get('desc', '')
            out_lines.append(f'\n[{title}]')
            out_lines.append(f'URL: {u}')
            out_lines.append(f'DESC: {desc}')

text = '\n'.join(out_lines)
with open('_research_corpus.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Corpus chars: {len(text)}')
print(f'Lines: {len(out_lines)}')
