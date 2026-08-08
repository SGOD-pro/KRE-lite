import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

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

simulated_llm_response = {
    "answer_draft": "The Transformer base model achieved a BLEU score of 25.8 on the WMT 2014 English-to-German translation task.",
    "citations": [
        {"page": 9, "section": "Model Variations", "quote": "For the base models, we used a single model obtained by averaging the last 5 che"}
    ],
    "premise_check": {"contains_claim": False, "claimed_value": None}
}

res = verify_citations(simulated_llm_response, context_chunks_by_page, question=q)
print(f"Verified result status: {res.get('status')}")
print(f"Verified citations: {len(res.get('citations', []))}")
if res.get('status') == 'refused':
    print(f"Reason: {res.get('reason')} - {res.get('message')}")
