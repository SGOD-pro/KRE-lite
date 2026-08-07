"""Trace exactly why 'what is transformers' gets refused."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search, invalidate_index
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, _quote_matches_chunk

Q = "what is transformers"

# Step 1: Retrieval (global, no session filter)
invalidate_index()
vec = vector_search(Q, top_k=20, session_id=None)
bm25 = bm25_search(Q, top_k=20, session_id=None)
print(f"Vector: {len(vec)} chunks, BM25: {len(bm25)} chunks")

# Step 2: Fusion
fused = reciprocal_rank_fusion([bm25, vec], top_k=15)
print(f"Fused: {len(fused)} chunks")

# Build context (same as planner.py)
context = {}
for chunk in fused:
    pg = chunk.get("page_number")
    if pg is not None:
        if pg in context:
            context[pg]["text"] += "\n" + chunk.get("text", "")
        else:
            context[pg] = {
                "page": pg,
                "section": chunk.get("section_title", "Untitled"),
                "text": chunk.get("text", ""),
                "source_file": chunk.get("source_file", ""),
                "chunk_id": chunk.get("chunk_id", f"page_{pg}"),
            }

print(f"\nContext pages: {sorted(context.keys())}")
for pg, data in sorted(context.items()):
    print(f"  Page {pg} [{data['section'][:50]}] ({data['source_file'][-30:]}): {data['text'][:100]}...")

# Step 3: LLM call
print("\n--- LLM Call ---")
llm_out = generate_answer(Q, context_chunks=context)
draft = llm_out.get("answer_draft", "")
cites = llm_out.get("citations", [])
print(f"answer_draft: {draft[:300]!r}")
print(f"citations count: {len(cites)}")
for i, c in enumerate(cites):
    print(f"  cite[{i}]: page={c.get('page')}, section={c.get('section','')[:50]!r}")
    print(f"    quote: {c.get('quote','')[:120]!r}")

# Step 4: Verification
print("\n--- Citation Verification ---")
if not cites:
    print("LLM RETURNED 0 CITATIONS -> auto-refuse!")
else:
    for i, c in enumerate(cites):
        pg = c.get("page")
        quote = c.get("quote", "")
        chunk_data = context.get(pg)
        if chunk_data:
            chunk_text = chunk_data.get("text", "")
            match = _quote_matches_chunk(quote, chunk_text)
            print(f"  cite[{i}] page={pg} match={match}")
            if not match:
                print(f"    QUOTE: {quote[:100]!r}")
                print(f"    CHUNK: {chunk_text[:150]!r}")
        else:
            print(f"  cite[{i}] page={pg} -> PAGE NOT IN CONTEXT! Available pages: {list(context.keys())}")

result = verify_citations(llm_out, context, question=Q)
print(f"\nFinal status: {result.get('status')}")
print(f"Final answer: {result.get('answer', result.get('message', ''))[:200]}")
