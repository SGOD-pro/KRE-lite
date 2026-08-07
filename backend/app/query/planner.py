"""
planner.py — Orchestrates the full query pipeline:
  1. Vector Retrieval (Qdrant semantic search)
  2. Pre-generation Guardrail  — out-of-scope check on semantic similarity
  3. BM25 Retrieval + RRF Fusion
  4. LLM Generation (Nova)
  5. Post-generation Guardrail  — citation verification (rapidfuzz)
"""
from __future__ import annotations

from typing import Any

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, REFUSAL_MESSAGE

# If the highest semantic match score is below this, the query is out of scope.
# Qdrant cosine scores range 0.0–1.0; below 0.3 is almost always unrelated.
SEMANTIC_SIMILARITY_THRESHOLD = 0.3


def answer_question(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Full RAG pipeline:
      1. Vector search for semantic similarity + pre-guardrail check.
      2. BM25 search + RRF fusion for top candidates.
      3. LLM generation with strict citations.
      4. Post-generation citation verifier to reject hallucinations.
    """
    # ── 1. Vector Search ─────────────────────────────────────────────────────
    vector_results = vector_search(question, top_k=20, session_id=session_id)

    # ── 2. Pre-generation Guardrail ──────────────────────────────────────────
    if not vector_results:
        return {
            "status": "refused",
            "answer": REFUSAL_MESSAGE,
            "citations": [],
        }

    highest_semantic_score = vector_results[0].get("vector_score", 0.0)
    if highest_semantic_score < SEMANTIC_SIMILARITY_THRESHOLD:
        print(f"[guardrail/pre] Query rejected — best semantic score: {highest_semantic_score:.3f}")
        return {
            "status": "refused",
            "answer": REFUSAL_MESSAGE,
            "citations": [],
        }

    # ── 3. BM25 Search + RRF Fusion ──────────────────────────────────────────
    bm25_results = bm25_search(question, top_k=20, session_id=session_id)
    fused_chunks_list = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)

    # Build context dict: chunk_id → {page, section, text, source_file}
    fused_chunks_dict: dict[str, dict] = {}
    for chunk in fused_chunks_list:
        fused_chunks_dict[chunk["chunk_id"]] = {
            "page": chunk.get("page_number"),
            "section": chunk.get("section_title"),
            "text": chunk.get("text", ""),
            "source_file": chunk.get("source_file", ""),
        }

    # ── 4. LLM Generation ────────────────────────────────────────────────────
    llm_output = generate_answer(question, context_chunks=fused_chunks_dict)

    # ── 5. Post-generation Guardrail (Citation Verifier) ─────────────────────
    final_output = verify_citations(llm_output, fused_chunks_dict)

    if final_output["status"] == "refused":
        print("[guardrail/post] Query refused — citations could not be verified in source chunks.")

    return final_output
