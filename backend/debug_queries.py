"""
debug_queries.py — Debug specific failing queries directly without HTTP.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, _quote_matches_chunk

FAILING_QUERIES = [
    "Who are the authors of the Attention Is All You Need paper?",
    "How many layers does the Transformer encoder have?",
    "How do transformers relate to convolutional neural networks?",
    "What is a vision transformer?",
    "What is data-dependent decay in linear attention?",
]

def debug_query(q: str):
    print(f"\n{'='*60}")
    print(f"QUERY: {q}")
    print(f"{'='*60}")

    vec = vector_search(q, top_k=5, session_id=None)
    bm25 = bm25_search(q, top_k=5, session_id=None)
    fused = reciprocal_rank_fusion([bm25, vec], top_k=5)

    print(f"Retrieved {len(fused)} chunks:")
    for chunk in fused:
        pg = chunk.get('page_number')
        sec = chunk.get('section_title','?')[:50]
        src = chunk.get('source_file','?')
        txt = chunk.get('text','')[:120]
        print(f"  page={pg} sec={sec!r} file={src}")
        print(f"  text: {txt}")

    if not fused:
        print("  >>> NO CHUNKS RETRIEVED — immediate refusal <<<")
        return

    # Run LLM
    context = {}
    for chunk in fused:
        pg = chunk.get('page_number')
        if pg is not None:
            if pg in context:
                context[pg]['text'] += '\n' + chunk.get('text','')
            else:
                context[pg] = {
                    'page': pg,
                    'section': chunk.get('section_title','Untitled'),
                    'text': chunk.get('text',''),
                    'source_file': chunk.get('source_file',''),
                    'chunk_id': chunk.get('chunk_id', f'page_{pg}'),
                }

    llm_out = generate_answer(q, context_chunks=context)
    print(f"\nLLM answer_draft: {llm_out.get('answer_draft','')[:200]}")
    print(f"LLM citations ({len(llm_out.get('citations',[]))}):")
    for c in llm_out.get('citations', []):
        page = c.get('page')
        quote = c.get('quote','')
        chunk_data = context.get(page, {})
        chunk_text = chunk_data.get('text','')
        match = _quote_matches_chunk(quote, chunk_text)
        print(f"  page={page} match={match}")
        print(f"  quote: {quote[:120]}")
        if not match:
            print(f"  chunk_text[:200]: {chunk_text[:200]}")

    final = verify_citations(llm_out, context, question=q)
    print(f"\nFINAL STATUS: {final.get('status')}")
    if final.get('status') == 'answered':
        print(f"Answer: {final.get('answer','')[:200]}")
    else:
        print(f"Reason: {final.get('message','')}")

for q in FAILING_QUERIES:
    debug_query(q)
