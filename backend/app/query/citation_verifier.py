"""
citation_verifier.py — The deterministic guardrail.
"""
from __future__ import annotations

from rapidfuzz import fuzz

FUZZ_THRESHOLD = 85.0
REFUSAL_MESSAGE = "I cannot answer this question based on the provided documents."


def verify_citations(
    llm_output: dict,
    retrieved_chunks: dict
) -> dict:
    """
    Verifies that the LLM's citations actually exist in the retrieved chunks.
    
    Args:
        llm_output: {"answer_draft": str, "citations": [...]}
        retrieved_chunks: {chunk_id: {"page": int, "section": str, "text": str}}
        
    Returns:
        {"status": "answered", "answer": str, "citations": [...]}
        or
        {"status": "refused", "reason": "no_grounded_answer", "message": str}
    """
    answer = llm_output.get("answer_draft", "")
    citations = llm_output.get("citations", [])

    if not citations:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE
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
        
        # Exact match
        if quote in context_text:
            verified_citations.append(citation)
            continue
            
        # Fuzzy match
        match_score = fuzz.partial_ratio(quote, context_text)
        if match_score >= 80.0:
            verified_citations.append(citation)

    if not verified_citations:
        return {
            "status": "refused",
            "reason": "no_grounded_answer",
            "message": REFUSAL_MESSAGE
        }

    return {
        "status": "answered",
        "answer": answer,
        "citations": verified_citations
    }
