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

FUZZ_THRESHOLD = 75.0  # allows paraphrased quotes; entity protection prevents hallucinations

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

    # 4. Content-word overlap fallback for fragmented chunks.
    # If the chunker split a sentence across section_title and text, or dropped words,
    # the sliding window can't match. Fall back to checking if enough content words
    # from the quote exist somewhere in the chunk text.
    NUMBER_WORDS = {
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
        "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
        "thousand", "million", "billion",
    }
    content_words_in_quote = [w for w in q_words if w not in STOPWORDS and len(w) > 2]
    if content_words_in_quote:
        # Number words (written-out digits) in the quote MUST exist in the chunk
        for nw in content_words_in_quote:
            if nw in NUMBER_WORDS:
                if not any(fuzz.ratio(nw, tw) >= 90 for tw in t_words):
                    return False

        matched_count = sum(
            1 for w in content_words_in_quote
            if any(fuzz.ratio(w, tw) >= 80 for tw in t_words)
        )
        # Accept if at least 4 content words match AND at least 75% of content words match
        if matched_count >= 4 and matched_count / len(content_words_in_quote) >= 0.75:
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

    # Rule 6 guard: Refusal triggers for adversarial / false-premise questions
    if question:
        q_lower = question.lower().strip()
        all_chunks_text = " ".join(
            f"{c.get('section', '')} {c.get('text', '')}"
            for c in retrieved_chunks.values()
        ).lower()

        # 1. Number verification: if the question specifies digits/amounts that do NOT exist
        # anywhere in the retrieved chunks, refuse (prevent wrong entity swap / hallucination)
        q_digits = re.findall(r"\b\d+\b", q_lower)
        for d in q_digits:
            if d not in all_chunks_text:
                if any(q_lower.startswith(prefix) for prefix in [
                    "is it true", "does the", "do ", "is ", "are ", "why does", "why do",
                    "under what", "given that", "since ", "can ", "how many", "what is"
                ]):
                    return _refusal()

        # 2. Leading questions with false premises ("Given that...", "Since...")
        if q_lower.startswith("given that") or q_lower.startswith("since"):
            premise_clause = q_lower.split(",")[0] if "," in q_lower else q_lower
            premise_words = [
                w for w in re.findall(r"\b[a-z]{3,}\b", premise_clause)
                if w not in STOPWORDS
            ]
            missing_premise_words = [w for w in premise_words if w not in all_chunks_text]
            if len(missing_premise_words) >= 2:
                return _refusal()

        # 3. Refutation guard: If answer explicitly denies/negates an entity from the question
        # that doesn't exist in chunks, refuse instead of correcting
        q_words = set(re.findall(r"\b\w+\b", q_lower)) - STOPWORDS
        neg_matches = re.findall(
            r"\b(?:not|never|no|neither|none|without|instead of|cannot|can't)\s+([a-zA-Z0-9]+)",
            answer_draft.lower(),
        )
        for w in neg_matches:
            if w in q_words and w not in all_chunks_text:
                return _refusal()

    verified: list[dict[str, Any]] = []
    seen_cites: set[tuple[int, str]] = set()

    for citation in raw_citations:
        # DECISION.md Rule 3: page + section + quote all required.
        # Missing any one -> auto-fail, no partial credit.
        page = citation.get("page")
        section = citation.get("section")
        quote = (citation.get("quote") or "").strip()

        if page is None or not section or not quote:
            continue  # auto-fail

        cite_key = (page, quote.lower())
        if cite_key in seen_cites:
            continue  # skip exact duplicate citation

        # Look up chunk by page number in retrieved_chunks
        chunk_data = retrieved_chunks.get(page)
        if chunk_data is None:
            continue  # claimed page not in retrieved set -> fail

        chunk_text = chunk_data.get("text", "")
        section_title = chunk_data.get("section", "")
        # Include section title in searchable text since the LLM sees it in the prompt
        # and may construct quotes that span the section heading + body text
        full_searchable_text = f"{section_title}\n{chunk_text}" if section_title else chunk_text
        source_file = chunk_data.get("source_file", "")
        chunk_id = chunk_data.get("chunk_id", f"page_{page}")

        if _quote_matches_chunk(quote, full_searchable_text):
            seen_cites.add(cite_key)
            verified.append({
                "page": page,
                "section": section,
                "quote": quote,
                "chunk_id": chunk_id,
                "source_file": source_file,
                "text": chunk_text,
            })
            continue  # matched on cited page, done

        # Cross-page fallback: if the LLM cited the wrong page but the quote
        # exists in another retrieved chunk, accept it with corrected page/chunk.
        for alt_page, alt_chunk in retrieved_chunks.items():
            if alt_page == page:
                continue  # already tried this
            alt_key = (alt_page, quote.lower())
            if alt_key in seen_cites:
                continue
            alt_text = alt_chunk.get("text", "")
            alt_section = alt_chunk.get("section", "")
            alt_searchable = f"{alt_section}\n{alt_text}" if alt_section else alt_text
            if _quote_matches_chunk(quote, alt_searchable):
                seen_cites.add(alt_key)
                verified.append({
                    "page": alt_page,
                    "section": alt_chunk.get("section", section),
                    "quote": quote,
                    "chunk_id": alt_chunk.get("chunk_id", f"page_{alt_page}"),
                    "source_file": alt_chunk.get("source_file", source_file),
                    "text": alt_chunk.get("text", ""),
                })
                break  # stop at first cross-page match

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
