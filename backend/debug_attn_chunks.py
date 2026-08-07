import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.ingest.store import get_all_chunks

session = 'reingest_1786120796'
chunks = get_all_chunks(session_id=session)

# Show all chunks from the Attention paper sorted by page
attn = [c for c in chunks if c.get('source_file','') == '1706.03762v7 (1).pdf']
print(f'Attention paper chunks: {len(attn)}')
for c in sorted(attn, key=lambda x: x.get('page_number',0)):
    pg = c['page_number']
    sec = c['section_title']
    txt = c['text'][:120]
    print(f'  p{pg:02d} [{sec[:50]}] {txt}')
