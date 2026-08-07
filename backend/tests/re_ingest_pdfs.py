"""
re_ingest_pdfs.py — Re-ingest PDFs with improved chunker into a fresh test session.
Prints the session_id so tests can reuse it.
"""
import sys
import os
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = 'http://localhost:8000'
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')

pdfs_to_ingest = [
    '1706.03762v7 (1).pdf',   # Attention Is All You Need (15 pages)
    '2304.10557v6.pdf',        # Introduction to Transformers (10 pages)
    '2507.19595v3.pdf',        # Efficient Attention (28 pages)
    '2103.16775v1.pdf',        # Survey (66 pages — takes longest)
]

session_id = f'reingest_{int(time.time())}'  # pre-generate so ALL files share the same session
total_chunks = 0
print(f'Target session_id: {session_id}')

for fname in pdfs_to_ingest:
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        print(f'SKIP (not found): {fname}')
        continue
    print(f'\nIngesting: {fname} ...', end='', flush=True)
    try:
        with open(path, 'rb') as fh:
            files = [('files', (fname, fh, 'application/pdf'))]
            form = {}
            if session_id:
                form['session_id'] = session_id
            resp = requests.post(f'{API_BASE}/ingest', files=files, data=form, timeout=600)

        if resp.status_code != 200:
            print(f' FAILED {resp.status_code}: {resp.text[:200]}')
            continue

        data = resp.json()

        for doc in data.get('documents', []):
            chunks = doc.get('chunks_created', 0)
            pages = doc.get('pages', 0)
            total_chunks += chunks
            print(f' OK — {chunks} chunks, {pages} pages')

    except requests.exceptions.Timeout:
        print(f' TIMEOUT after 600s')
    except Exception as exc:
        print(f' ERROR: {exc}')

print(f'\n{"="*50}')
print(f'SESSION_ID: {session_id}')
print(f'TOTAL_CHUNKS: {total_chunks}')
print(f'{"="*50}')
print(f'\nRun tests with:')
print(f'  python tests\\e2e_rag_test.py --session {session_id}')
