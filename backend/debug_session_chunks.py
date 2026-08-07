import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.ingest.store import get_all_chunks

session = 'reingest_1786120796'
chunks = get_all_chunks(session_id=session)
print(f'Session chunks: {len(chunks)}')

# BLEU table
bleu = [c for c in chunks if 'bleu' in c.get('text','').lower() or 'BLEU' in c.get('text','')]
print(f'\nBLEU chunks: {len(bleu)}')
for c in bleu[:4]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:300]
    src = c['source_file']
    print(f'  page={pg} sec={sec!r} file={src}')
    print(f'  {txt}')
    print()

# 512 d_model
d512 = [c for c in chunks if '512' in c.get('text','')]
print(f'd_model=512 chunks: {len(d512)}')
for c in d512[:3]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:250]
    src = c['source_file']
    print(f'  page={pg} sec={sec!r} file={src}')
    print(f'  {txt}')
    print()

# Vision transformer
vis = [c for c in chunks if 'vision transformer' in c.get('text','').lower() or 'ViT' in c.get('text','')]
print(f'Vision transformer chunks: {len(vis)}')
for c in vis[:3]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:250]
    src = c['source_file']
    print(f'  page={pg} sec={sec!r} file={src}')
    print(f'  {txt}')
    print()

# Data-dependent decay
ddd = [c for c in chunks if 'data-dependent' in c.get('text','').lower()]
print(f'Data-dependent decay chunks: {len(ddd)}')
for c in ddd[:4]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:300]
    src = c['source_file']
    print(f'  page={pg} sec={sec!r} file={src}')
    print(f'  {txt}')
    print()

# Encoder N=6
enc6 = [c for c in chunks if 'N = 6' in c.get('text','') or 'n = 6' in c.get('text','').lower()]
print(f'N=6 encoder chunks: {len(enc6)}')
for c in enc6[:3]:
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:250]
    src = c['source_file']
    print(f'  page={pg} sec={sec!r} file={src}')
    print(f'  {txt}')
    print()
