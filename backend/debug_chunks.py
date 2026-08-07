import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.ingest.store import get_all_chunks

chunks = get_all_chunks()

# Look at page 1 chunks from the attention paper to understand authors chunk
p1 = [c for c in chunks if c.get('source_file','') == '1706.03762v7 (1).pdf' and c.get('page_number') == 1]
print('=== PAGE 1 chunks (authors page) ===')
for c in p1[:3]:
    cid = c.get('chunk_id','?')
    sec = c.get('section_title','?')
    txt = c.get('text','')[:600]
    print(f'chunk_id={cid}  section={sec}')
    print(f'text: {txt}')
    print()

# Look for encoder 6 layers text
p3 = [c for c in chunks if c.get('source_file','') == '1706.03762v7 (1).pdf' and c.get('page_number') == 3]
print('=== PAGE 3 chunks (encoder section) ===')
for c in p3[:3]:
    sec = c.get('section_title','?')
    txt = c.get('text','')[:400]
    print(f'section={sec}')
    print(f'text: {txt}')
    print()

# Look at 2304.10557 (Turner paper) CNNs content
cnn_chunks = [c for c in chunks if c.get('source_file','') == '2304.10557v6.pdf']
print(f'=== Turner paper chunks: {len(cnn_chunks)} total ===')
for c in cnn_chunks[:5]:
    pg = c.get('page_number')
    sec = c.get('section_title','?')
    txt = c.get('text','')[:200]
    print(f'page={pg} section={sec}')
    print(f'text: {txt}')
    print()

# Data-dependent decay
decay_chunks = [c for c in chunks if 'data-dependent' in c.get('text','').lower() or 'data dependent' in c.get('text','').lower()]
print(f'=== Data-dependent decay chunks: {len(decay_chunks)} ===')
for c in decay_chunks[:3]:
    pg = c.get('page_number')
    sec = c.get('section_title','?')
    txt = c.get('text','')[:300]
    print(f'page={pg} section={sec} file={c.get("source_file")}')
    print(f'text: {txt}')
    print()
