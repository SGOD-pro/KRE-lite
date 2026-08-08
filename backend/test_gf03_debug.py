import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.query.planner import answer_question
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, _quote_matches_chunk
from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion

q = "In Attention Is All You Need, what BLEU score did the Transformer base model achieve on the WMT 2014 English-to-German translation task?"

v_res = vector_search(q, top_k=15)
b_res = bm25_search(q, top_k=20)
fused = reciprocal_rank_fusion([b_res, v_res], top_k=15)

context_chunks_by_page = {}
for chunk in fused:
    p = chunk.get("page_number")
    if p is not None:
        t = (chunk.get("text") or "").strip()
        if p in context_chunks_by_page:
            if t not in context_chunks_by_page[p]["text"]:
                context_chunks_by_page[p]["text"] += "\n\n" + t
        else:
            context_chunks_by_page[p] = {
                "page": p,
                "section": chunk.get("section_title", "Untitled"),
                "text": t,
                "source_file": chunk.get("source_file", ""),
                "chunk_id": chunk.get("chunk_id", f"page_{p}"),
            }

print(f"Context pages: {list(context_chunks_by_page.keys())}")
for p, c in context_chunks_by_page.items():
    print(f"Page {p} [{c['section']}]: len={len(c['text'])}")

for i in range(5):
    print(f"\n--- TRIAL {i+1} ---")
    llm_out = generate_answer(q, context_chunks_by_page)
    print(f"LLM draft: {llm_out.get('answer_draft')}")
    cites = llm_out.get('citations', [])
    print(f"LLM citations ({len(cites)}): {cites}")
    
    verified = verify_citations(llm_out, context_chunks_by_page)
    print(f"Verified Status: {verified.get('status')}")
    if verified.get('status') == 'refused':
        print(f"Refusal: {verified}")
        for c in cites:
            cp = c.get('page')
            cq = c.get('quote')
            chunk_t = context_chunks_by_page.get(cp, {}).get('text', '')
            match = _quote_matches_chunk(cq, chunk_t)
            print(f"  Quote on p.{cp} matched chunk: {match}")
            print(f"  Quote: '{cq}'")
            print(f"  Chunk text sample: '{chunk_t[:200]}'")
