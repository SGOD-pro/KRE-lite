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
from app.query.security_guardrail import detect_prompt_injection, sanitize_input_text


def answer_question(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Executes the end-to-end question answering pipeline:
      0. Screen against Prompt Injection & Jailbreak attacks.
      1. Retrieve top vector candidates from Qdrant.
      2. Retrieve top BM25 candidates from keyword store.
      3. Fuse candidates using Reciprocal Rank Fusion.
      4. If no relevant chunks exist, refuse immediately.
      5. Generate structured answer draft with citations using LLM.
      6. Verifies citation quotes against actual chunk text deterministically.
      7. Returns verified answer or structured refusal.
    """
    raw_question = question.strip() if question else ""
    if not raw_question:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    # ── 0. Prompt Injection & Security Defense ──────────────────────────────
    is_injection, reason = detect_prompt_injection(raw_question)
    if is_injection:
        print(f"[SECURITY] REFUSAL: {reason}")
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    clean_question = sanitize_input_text(raw_question)

    print(f"\n[QUERY] Starting query pipeline for session: {session_id}")
    print(f"[QUERY] Question: {clean_question!r}")
    
    # ── 1. Retrieval (Hybrid Vector + BM25) ──────────────────────────────────
    # If a session_id is provided, search strictly within the session.
    # If session_id is None, search globally across all collections.
    if session_id:
        vector_session = vector_search(clean_question, top_k=15, session_id=session_id)
        bm25_session   = bm25_search(clean_question,   top_k=15, session_id=session_id)
        all_result_lists = [bm25_session, vector_session]
        print(f"[QUERY] Session '{session_id}': vector={len(vector_session)}, bm25={len(bm25_session)}")
    else:
        vector_global  = vector_search(clean_question, top_k=20, session_id=None)
        bm25_global    = bm25_search(clean_question,   top_k=20, session_id=None)
        all_result_lists = [bm25_global, vector_global]
        print(f"[QUERY] Global: vector={len(vector_global)}, bm25={len(bm25_global)}")

    # ── 2. Fusion ───────────────────────────────────────────────────────────
    fused_chunks_list = reciprocal_rank_fusion(all_result_lists, top_k=15)
    print(f"[QUERY] Rank fusion selected {len(fused_chunks_list)} chunks")

    if not fused_chunks_list:
        print("[QUERY] REFUSAL: No chunks found during retrieval/fusion.")
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
            chunk_text = (chunk.get("text") or "").strip()
            if not chunk_text:
                continue
            if page_num in context_chunks_by_page:
                existing_text = context_chunks_by_page[page_num]["text"]
                # Only append if chunk_text is not already contained in existing_text
                if chunk_text not in existing_text and existing_text not in chunk_text:
                    context_chunks_by_page[page_num]["text"] += "\n\n" + chunk_text
                elif len(chunk_text) > len(existing_text):
                    context_chunks_by_page[page_num]["text"] = chunk_text
            else:
                context_chunks_by_page[page_num] = {
                    "page": page_num,
                    "section": chunk.get("section_title", "Untitled"),
                    "text": chunk_text,
                    "source_file": chunk.get("source_file", ""),
                    "chunk_id": chunk.get("chunk_id", f"page_{page_num}"),
                }

    if not context_chunks_by_page:
        print("[QUERY] REFUSAL: Context chunks by page is empty.")
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE,
        }

    # ── 3. LLM Structured Generation (Single Call) ──────────────────────────
    print(f"[QUERY] Sending {len(context_chunks_by_page)} pages of context to LLM...")
    llm_output = generate_answer(clean_question, context_chunks=context_chunks_by_page)
    
    # DEBUG: Show exactly what the LLM returned
    answer_draft = llm_output.get("answer_draft", "")
    llm_citations = llm_output.get("citations", [])
    print(f"[QUERY] LLM answer_draft: {answer_draft[:200]!r}")
    print(f"[QUERY] LLM citations count: {len(llm_citations)}")
    for i, c in enumerate(llm_citations):
        print(f"[QUERY]   cite[{i}]: page={c.get('page')}, section={c.get('section','')[:40]!r}, quote={c.get('quote','')[:80]!r}")

    # ── 4. Deterministic Citation Verification ──────────────────────────────
    final_output = verify_citations(llm_output, context_chunks_by_page, question=clean_question)
    print(f"[QUERY] Final output status: {final_output.get('status')}")
    
    if final_output.get("status") == "refused":
        print(f"[QUERY] REFUSAL REASON: {final_output.get('message')}")

    return final_output
