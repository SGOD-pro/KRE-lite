import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.ingest.chunker import chunk_document

chunks = chunk_document(r'd:\WORK\hackathon\data\1706.03762v7 (1).pdf')
print(f'Total chunks: {len(chunks)}')

# Look at page 1
p1 = [c for c in chunks if c['page_number'] == 1]
print(f'\nPage 1 chunks ({len(p1)}):')
for c in p1:
    sec = c['section_title']
    txt = c['text'][:200]
    print(f'  section={sec!r}')
    print(f'  text: {txt}')
    print()

# Encoder section
enc = [c for c in chunks if c['page_number'] == 3]
print(f'Page 3 chunks ({len(enc)}):')
for c in enc[:5]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:200]
    print(f'  page={pg} section={sec!r}')
    print(f'  text: {txt}')
    print()
