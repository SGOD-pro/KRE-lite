"""
planner.py — Orchestrates the full query pipeline (Retrieval -> Pre-Guardrail -> LLM -> Post-Guardrail).
"""
from __future__ import annotations

from typing import Any

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, REFUSAL_MESSAGE

# If the highest semantic match score is below this, the query is completely out of scope.
# Note: Qdrant cosine similarity typically ranges from -1.0 to 1.0 (often 0.0 to 1.0).
# A score below 0.3 for modern text embeddings usually means completely unrelated.
SEMANTIC_SIMILARITY_THRESHOLD = 0.3


def answer_question(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    1. Vector Retrieval
    2. Pre-generation Guardrail (Out of scope check)
    3. BM25 Retrieval & RRF Fusion
    4. LLM Generation
    5. Post-generation Guardrail (Citation Verification)
    """
    # 1. Vector Search
    vector_results = vector_search(question, top_k=20, session_id=session_id)
    
    # 2. Pre-generation Guardrail (Out of Scope Check)
    if not vector_results:
        return {"status": "refused", "answer": REFUSAL_MESSAGE, "citations": []}
        
    highest_semantic_score = vector_results[0].get("vector_score", 0.0)
    if highest_semantic_score < SEMANTIC_SIMILARITY_THRESHOLD:
        return {
            "status": "refused",
            "answer": REFUSAL_MESSAGE,
            "citations": []
        }
        
    # 3. BM25 Search & Hybrid Fusion
    bm25_results = bm25_search(question, top_k=20, session_id=session_id)
    fused_chunks_list = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)
    
    # Convert fused_chunks_list to dict mapping chunk_id to dict with page, section, text
    fused_chunks_dict = {}
    for chunk in fused_chunks_list:
        fused_chunks_dict[chunk["chunk_id"]] = {
            "page": chunk.get("page_number"),
            "section": chunk.get("section_title"),
            "text": chunk.get("text")
        }
    
    # 4. LLM Generation
    llm_output = generate_answer(question, context_chunks=fused_chunks_dict)
    
    # 5. Post-generation Guardrail (Citation Verifier)
    final_output = verify_citations(llm_output, fused_chunks_dict)
    
    # Add status field
    if final_output.get("status") == "refused":
        pass # already set by verify_citations
    else:
        # If verify_citations returns answered, we can pass it through or adjust
        pass
        
    return final_output
