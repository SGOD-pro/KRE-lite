"""
debug_failing.py — Trace the 5 remaining failing queries with session filter.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search, invalidate_index
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, _quote_matches_chunk

SESSION = 'reingest_1786120796'

QUERIES = [
    ("1.5 Encoder layers",   "How many layers does the Transformer encoder have?"),
    ("1.7 d_model 512",      "What is the d_model dimension in the base Transformer?"),
    ("2.3 Vision transformer","What is a vision transformer?"),
    ("4.1 Self-attn O(n^2)", "What is the computational complexity (big-O) of the self-attention mechanism?"),
    ("4.3 Data-dep decay",   "What is data-dependent decay in linear attention?"),
    ("7.1 Self-attn vs RNN", "How does self-attention compare to recurrent networks in complexity?"),
]

invalidate_index()  # Force BM25 rebuild for this session

for label, q in QUERIES:
    print(f"\n{'='*60}")
    print(f"[{label}] {q}")

    vec  = vector_search(q, top_k=5, session_id=SESSION)
    bm25 = bm25_search(q,  top_k=5, session_id=SESSION)
    fused = reciprocal_rank_fusion([bm25, vec], top_k=5)

    print(f"Retrieved {len(fused)} chunks:")
    for c in fused:
        pg  = c.get('page_number')
        sec = c.get('section_title','?')[:55]
        src = c.get('source_file','?')[-25:]
        txt = c.get('text','')[:100]
        print(f"  p{pg:02d} [{sec}] ({src})")
        print(f"       {txt}")

    context = {}
    for c in fused:
        pg = c.get('page_number')
        if pg is not None:
            if pg in context:
                context[pg]['text'] += '\n' + c.get('text','')
            else:
                context[pg] = {
                    'page': pg, 'section': c.get('section_title','?'),
                    'text': c.get('text',''), 'source_file': c.get('source_file',''),
                    'chunk_id': c.get('chunk_id', f'p{pg}'),
                }

    llm = generate_answer(q, context_chunks=context)
    ad = llm.get('answer_draft','')[:150]
    cits = llm.get('citations', [])
    print(f"\nLLM draft: {ad}")
    for c in cits:
        pg    = c.get('page')
        quote = c.get('quote','')
        ct    = context.get(pg, {}).get('text', '')
        match = _quote_matches_chunk(quote, ct)
        print(f"  cite p{pg} match={match} quote={quote[:80]}")
        if not match:
            print(f"  chunk: {ct[:120]}")

    out = verify_citations(llm, context, question=q)
    print(f"STATUS: {out.get('status')} | {out.get('answer','')[:100] or out.get('message','')[:100]}")
