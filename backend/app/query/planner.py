"""
planner.py — Orchestrates the full query pipeline:
  1. Semantic vector retrieval (Qdrant)
  2. Keyword BM25 retrieval
  3. Hybrid rank fusion (Reciprocal Rank Fusion)
  4. Structured LLM Generation (NVIDIA Build / OpenRouter / Bedrock Nova)
  5. Post-generation Citation Verification (deterministic fuzzy guardrail)

Output matches API.md / POST /query contracts exactly:
  Answered:
    {"status": "answered", "answer": str, "citations": [{"page": int, "section": str, "quote": str, "chunk_id": str}]}
  Refused:
    {"status": "refused", "reason": "no_grounded_answer", "message": str}
"""
from __future__ import annotations

from typing import Any

from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations, REFUSAL_MESSAGE


def answer_question(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Executes the end-to-end question answering pipeline:
      1. Retrieve top vector candidates from Qdrant.
      2. Retrieve top BM25 candidates from keyword store.
      3. Fuse candidates using Reciprocal Rank Fusion.
      4. If no relevant chunks exist, refuse immediately.
      5. Generate structured answer draft with citations using LLM.
      6. Verifies citation quotes against actual chunk text deterministically.
      7. Returns verified answer or structured refusal.
    """
    clean_question = question.strip() if question else ""
    if not clean_question:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    # ── 1. Retrieval (Hybrid Vector + BM25) ──────────────────────────────────
    vector_results = vector_search(clean_question, top_k=20, session_id=session_id)
    bm25_results = bm25_search(clean_question, top_k=20, session_id=session_id)

    # ── 2. Fusion ───────────────────────────────────────────────────────────
    fused_chunks_list = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)

    if not fused_chunks_list:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    # Format context dictionary keyed by page_number (int) for LLM and verifier
    # { page_number: {"section": str, "text": str, "source_file": str, "chunk_id": str} }
    context_chunks_by_page: dict[int, dict[str, Any]] = {}
    for chunk in fused_chunks_list:
        page_num = chunk.get("page_number")
        if page_num is not None:
            # If multiple chunks share the same page, combine texts
            if page_num in context_chunks_by_page:
                context_chunks_by_page[page_num]["text"] += "\n" + chunk.get("text", "")
            else:
                context_chunks_by_page[page_num] = {
                    "page": page_num,
                    "section": chunk.get("section_title", "Untitled"),
                    "text": chunk.get("text", ""),
                    "source_file": chunk.get("source_file", ""),
                    "chunk_id": chunk.get("chunk_id", f"page_{page_num}"),
                }

    if not context_chunks_by_page:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    # ── 3. LLM Structured Generation (Single Call) ──────────────────────────
    llm_output = generate_answer(clean_question, context_chunks=context_chunks_by_page)

    # ── 4. Deterministic Citation Verification ──────────────────────────────
    final_output = verify_citations(llm_output, context_chunks_by_page, question=clean_question)

    return final_output
