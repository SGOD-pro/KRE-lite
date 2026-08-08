import os
import sys
import hashlib

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.query.bm25_retriever import bm25_search, _tokenize, _build_index
from app.query.vector_retriever import vector_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from benchmark_evaluation import GROUNDED_FACT_SET

def deduplicated_bm25(query, top_k=20, fetch_k=100):
    # Fetch larger set, deduplicate text
    from app.query import bm25_retriever
    if bm25_retriever._bm25_index is None:
        _build_index()
    scores = bm25_retriever._bm25_index.get_scores(_tokenize(query))
    scored = sorted(zip(bm25_retriever._indexed_chunks, scores), key=lambda x: x[1], reverse=True)
    
    seen_texts = set()
    deduped = []
    for chunk, score in scored:
        if score <= 0:
            break
        text_hash = hashlib.md5(chunk["text"].strip().encode()).hexdigest()
        if text_hash not in seen_texts:
            seen_texts.add(text_hash)
            c = chunk.copy()
            c["bm25_score"] = float(score)
            deduped.append(c)
            if len(deduped) >= top_k:
                break
    return deduped

def deduplicated_vector(query, top_k=20, fetch_k=100):
    from app.shared.config import get_qdrant_client
    from app.ingest.embed_service import embed_query
    from app.ingest.store import COLLECTION_NAME
    
    qdrant = get_qdrant_client()
    query_vec = embed_query(query)
    points = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vec,
        limit=fetch_k,
        with_payload=True,
    ).points
    
    seen_texts = set()
    deduped = []
    for hit in points:
        payload = hit.payload or {}
        text = payload.get("text")
        if not text:
            continue
        text_hash = hashlib.md5(text.strip().encode()).hexdigest()
        if text_hash not in seen_texts:
            seen_texts.add(text_hash)
            chunk = {
                "chunk_id": payload.get("chunk_id", ""),
                "source_file": payload.get("source_file", ""),
                "page_number": payload.get("page_number", 1),
                "section_title": payload.get("section_title", ""),
                "text": text,
                "vector_score": float(hit.score),
            }
            deduped.append(chunk)
            if len(deduped) >= top_k:
                break
    return deduped

print("=" * 80)
print("TESTING DEDUPLICATED RETRIEVAL FOR ALL 5 GROUNDED FACT QUESTIONS")
print("=" * 80)

for item in GROUNDED_FACT_SET:
    qid = item["id"]
    q = item["question"]
    print(f"\n--- [{qid}] {q} ---")
    
    v_res = deduplicated_vector(q, top_k=15, fetch_k=100)
    b_res = deduplicated_bm25(q, top_k=15, fetch_k=200)
    
    fused = reciprocal_rank_fusion([b_res, v_res], top_k=10)
    
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
        print(f"  Page {p} [{c['section']}]: len={len(c['text'])} sample='{c['text'][:100]}...'")
        
    llm_out = generate_answer(q, context_chunks_by_page)
    print(f"LLM Answer: {llm_out.get('answer_draft')[:120]}...")
    print(f"LLM Citations: {llm_out.get('citations')}")
