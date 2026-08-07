import sys; sys.stdout.reconfigure(encoding='utf-8')
from app.ingest.store import get_all_chunks

# no session filter - all chunks
chunks = get_all_chunks()
attn = [c for c in chunks if '1706' in c.get('source_file','') and c.get('session_id') == 'reingest_1786120796']
print(f'Attention paper chunks in reingest session: {len(attn)}')

# What filenames are stored under reingest session?
reingest = [c for c in chunks if c.get('session_id') == 'reingest_1786120796']
files = {}
for c in reingest:
    f = c.get('source_file','?')
    files[f] = files.get(f,0)+1
print('Files under reingest_1786120796:')
for f,n in sorted(files.items()):
    print(f'  {repr(f)}: {n}')

# Any reingest session chunks at all?
print(f'\nTotal reingest chunks: {len(reingest)}')
