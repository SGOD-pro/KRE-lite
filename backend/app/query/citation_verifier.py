"""
citation_verifier.py — The deterministic post-generation guardrail.

ARCHITECTURE.md design:
  1. Look up chunk by (page, section) from the retrieved chunks.
  2. Fuzzy-match quote against that chunk's raw text
     (case-insensitive, >= 90% token overlap via simple ratio — NOT exact string match,
     with content-word verification to prevent entity-swap hallucinations).
  3. PASS -> citation kept, enriched with chunk_id + source_file.
  4. FAIL -> citation dropped.
  Output: >=1 survived -> answered; 0 survived -> refusal.

This is pure deterministic code — NO second LLM call (DECISION.md Rules 4 & 9).
The verifier has no bypass flag, no "trust mode" (DECISION.md Rule 4).
LLM confidence signals in the output are completely ignored (DECISION.md Rule 6).

Retrieved chunks format (the source of truth passed in from planner.py):
  { page_number (int): {section, text, source_file, chunk_id} }

LLM structured output format (from API.md "Internal Contract"):
  { answer_draft: str, citations: [{page: int, section: str, quote: str}] }
  Note: the LLM does NOT return chunk_id — that comes from the store lookup.
"""
from __future__ import annotations

import re
from typing import Any

from thefuzz import fuzz

FUZZ_THRESHOLD = 90.0

REFUSAL_MESSAGE = (
    "I don't have enough information in the provided documents to answer that."
)

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "by",
    "for", "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
    "over", "under", "again", "further", "then", "once", "here", "there", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "as", "of"
}


def _normalize(text: str) -> str:
    """Collapse whitespace and lowercase for fair comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _quote_matches_chunk(quote: str, chunk_text: str) -> bool:
    """
    Returns True if quote is verifiably grounded in chunk_text.

    Verification steps:
    1. Exact substring match (case-insensitive, whitespace-normalized).
    2. Punctuation-stripped substring match.
    3. Sliding window fuzzy matching (>=90% ratio) with content-word verification
       to strictly prevent entity/number swap hallucinations (DECISION.md Rule 6).
    """
    q = _normalize(quote)
    t = _normalize(chunk_text)

    if not q or not t:
        return False

    # 1. Exact substring match
    if q in t:
        return True

    # 2. Punctuation-stripped exact substring match
    q_nopunct = re.sub(r"[^\w\s]", "", q)
    t_nopunct = re.sub(r"[^\w\s]", "", t)
    if q_nopunct in t_nopunct:
        return True

    # 3. Token-level window fuzzy match with entity protection
    q_words = q_nopunct.split()
    t_words = t_nopunct.split()
    if not q_words or not t_words:
        return False

    # Any digits in quote MUST be present in chunk
    q_nums = re.findall(r"\b\d+\b", q)
    for num in q_nums:
        if num not in t:
            return False

    n = len(q_words)
    # Slide window of roughly same token length
    for win_len in range(max(1, n - 2), min(len(t_words) + 1, n + 3)):
        for i in range(len(t_words) - win_len + 1):
            window = t_words[i : i + win_len]
            win_str = " ".join(window)

            score = fuzz.ratio(q_nopunct, win_str)
            if score >= FUZZ_THRESHOLD:
                # Ensure no non-stopword token was replaced by a totally different word
                has_fake_entity = False
                for qw in q_words:
                    if qw not in STOPWORDS and len(qw) > 2:
                        if not any(fuzz.ratio(qw, tw) >= 80 for tw in window):
                            has_fake_entity = True
                            break
                if not has_fake_entity:
                    return True

    return False


def verify_citations(
    llm_output: dict[str, Any],
    retrieved_chunks: dict[int, dict[str, Any]],
    question: str = "",
) -> dict[str, Any]:
    """
    Deterministically verifies LLM citations against retrieved context chunks.

    Args:
        llm_output: dict with "answer_draft" (str) and "citations" (list of dicts).
        retrieved_chunks: dict keyed by page_number (int).
                          Each value: {section, text, source_file, chunk_id}.
        question: Optional user query string to guard against unsupported entity refutations.

    Returns API.md-compliant shape:
        Answered:  {"status": "answered", "answer": str, "citations": [...]}
        Refused:   {"status": "refused", "reason": "no_grounded_answer", "message": str}
    """
    answer_draft = llm_output.get("answer_draft", "")
    raw_citations = llm_output.get("citations", [])

    # No citations returned by LLM -> immediate refusal
    if not raw_citations:
        return _refusal()

    # Rule 6 guard: If answer refutes/denies an entity from question that doesn't exist in chunks, refuse
    if question:
        all_chunks_text = " ".join(c.get("text", "") for c in retrieved_chunks.values()).lower()
        q_words = set(re.findall(r"\b\w+\b", question.lower())) - STOPWORDS
        neg_matches = re.findall(
            r"\b(?:not|never|no|neither|none|without|instead of)\s+([a-zA-Z0-9]+)",
            answer_draft.lower(),
        )
        for w in neg_matches:
            if w in q_words and w not in all_chunks_text:
                return _refusal()

    verified: list[dict[str, Any]] = []

    for citation in raw_citations:
        # DECISION.md Rule 3: page + section + quote all required.
        # Missing any one -> auto-fail, no partial credit.
        page = citation.get("page")
        section = citation.get("section")
        quote = citation.get("quote", "")

        if page is None or not section or not quote:
            continue  # auto-fail

        # Look up chunk by page number in retrieved_chunks
        chunk_data = retrieved_chunks.get(page)
        if chunk_data is None:
            continue  # claimed page not in retrieved set -> fail

        chunk_text = chunk_data.get("text", "")
        source_file = chunk_data.get("source_file", "")
        chunk_id = chunk_data.get("chunk_id", f"page_{page}")

        if _quote_matches_chunk(quote, chunk_text):
            verified.append({
                "page": page,
                "section": section,
                "quote": quote,
                "chunk_id": chunk_id,
                "source_file": source_file,
                "text": chunk_text,
            })
        # else: silently drop this citation

    if not verified:
        return _refusal()

    return {
        "status": "answered",
        "answer": answer_draft,
        "citations": verified,
    }


def _refusal() -> dict[str, Any]:
    """Returns the exact API.md refusal shape (DECISION.md Rule 5)."""
    return {
        "status": "refused",
        "reason": "no_grounded_answer",
        "message": REFUSAL_MESSAGE,
    }
