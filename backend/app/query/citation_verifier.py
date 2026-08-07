"""
citation_verifier.py — The deterministic post-generation guardrail.

Verifies that LLM citations actually exist in the retrieved chunks.
Enriches each verified citation with the full chunk text and source_file
so the frontend SourceViewer can display real (non-hallucinated) content.
"""
from __future__ import annotations

from rapidfuzz import fuzz

FUZZ_THRESHOLD = 80.0
REFUSAL_MESSAGE = "I cannot answer this question based on the provided documents."


def verify_citations(
    llm_output: dict,
    retrieved_chunks: dict
) -> dict:
    """
    Verifies that the LLM's citations actually exist in the retrieved chunks.

    Args:
        llm_output: {"answer_draft": str, "citations": [...]}
        retrieved_chunks: {chunk_id: {"page": int, "section": str, "text": str, "source_file": str}}

    Returns:
        {"status": "answered", "answer": str, "citations": [...enriched citations]}
        or
        {"status": "refused", "answer": str, "citations": []}
    """
    answer = llm_output.get("answer_draft", "")
    citations = llm_output.get("citations", [])

    if not citations:
        return {
            "status": "refused",
            "answer": REFUSAL_MESSAGE,
            "citations": [],
        }

    verified_citations = []

    for citation in citations:
        chunk_id = citation.get("chunk_id")
        page = citation.get("page")
        section = citation.get("section")
        quote = citation.get("quote", "")

        # Must have page and section per test requirements
        if page is None or not section:
            continue

        if not quote or chunk_id not in retrieved_chunks:
            continue

        chunk_data = retrieved_chunks[chunk_id]
        context_text = chunk_data.get("text", "")
        source_file = chunk_data.get("source_file", "")

        matched = False

        # Exact substring match — gold standard
        if quote in context_text:
            matched = True

        # Fuzzy match fallback — catches minor whitespace/formatting differences
        if not matched:
            match_score = fuzz.partial_ratio(quote, context_text)
            if match_score >= FUZZ_THRESHOLD:
                matched = True

        if matched:
            # Enrich citation with full chunk text and source file for SourceViewer
            verified_citations.append({
                "chunk_id": chunk_id,
                "page": page,
                "section": section,
                "quote": quote,
                "text": context_text,        # real chunk text — prevents hallucination in UI
                "source_file": source_file,  # which PDF this came from
            })

    if not verified_citations:
        return {
            "status": "refused",
            "answer": REFUSAL_MESSAGE,
            "citations": [],
        }

    return {
        "status": "answered",
        "answer": answer,
        "citations": verified_citations,
    }
