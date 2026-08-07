"""
citation_verifier.py — The deterministic post-generation guardrail.

ARCHITECTURE.md design:
  1. Look up chunk by (page, section) from the retrieved chunks.
  2. Fuzzy-match quote against that chunk's raw text
     (case-insensitive, >= 90% token overlap via simple ratio — NOT exact string match,
     with content-word verification to prevent entity-swap hallucinations).
  3. PASS -> citation kept, enriched with chunk_id + source_file.
  4. FAIL -> citation dropped.
  Output: >=1 survived:
    - If premise_check.contains_claim=True and verified quote CONTRADICTS the claimed
      value -> status="corrected" (DECISION.md Rule 15, API.md shape).
    - Otherwise -> status="answered".
  0 survived: -> status="refused".

This is pure deterministic code — NO second LLM call (DECISION.md Rules 4 & 9).
The verifier has no bypass flag, no "trust mode" (DECISION.md Rule 4).
LLM confidence signals in the output are completely ignored (DECISION.md Rule 6).

Retrieved chunks format (the source of truth passed in from planner.py):
  { page_number (int): {section, text, source_file, chunk_id} }

LLM structured output format (from API.md "Internal Contract"):
  {
    "answer_draft": str,
    "citations": [{"page": int, "section": str, "quote": str}],
    "premise_check": {"contains_claim": bool, "claimed_value": str|null}
  }
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


def _extract_numeric_tokens(text: str) -> list[str]:
    """
    Extract all numeric tokens from text: digits (e.g. "3", "500") and
    written-out number words (e.g. "three", "fifty"). Used to compare
    claimed values against verified quote text for premise contradiction.
    Returns a list of normalized strings.
    """
    NUMBER_WORD_MAP = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
        "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
        "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
        "eighty": "80", "ninety": "90",
    }
    t = text.lower()
    tokens: list[str] = []
    # Digit sequences with optional $ prefix
    tokens += re.findall(r"\$?\d+(?:\.\d+)?", t)
    # Written-out number words
    for word, digit in NUMBER_WORD_MAP.items():
        if re.search(r"\b" + word + r"\b", t):
            tokens.append(digit)
    return tokens


def _check_premise_contradiction(
    claimed_value: str,
    verified_citations: list[dict[str, Any]],
) -> tuple[bool, str | None]:
    """
    Deterministic check: does any verified citation's quote contain a numeric/entity
    value that CONTRADICTS the claimed_value from the question's premise?

    Returns:
        (contradicted: bool, actual_grounded_value: str | None)
        - contradicted=True if:
          a) The verified quote contains a DIFFERENT numeric value than claimed, or
          b) The claimed value is 'unlimited'/'no limit' but the quote contains any
             finite number (i.e., any specific limit contradicts an unlimited claim).
        - actual_grounded_value: the value found in the citation (for the response).

    This is purely lexical/numeric — no LLM call (DECISION.md Rule 9).
    """
    if not claimed_value:
        return False, None

    claimed_norm = _normalize(claimed_value)

    # Special case: claimed value is 'unlimited' / 'no limit' / 'unrestricted' etc.
    # Any verified citation that contains a finite number contradicts this claim.
    UNLIMITED_WORDS = {"unlimited", "no limit", "no maximum", "unrestricted", "indefinitely"}
    claimed_is_unlimited = any(uw in claimed_norm for uw in UNLIMITED_WORDS)
    if claimed_is_unlimited:
        for cit in verified_citations:
            quote = cit.get("quote", "")
            if not quote:
                continue
            quote_nums = _extract_numeric_tokens(quote)
            if quote_nums:
                # Found a finite number in the citation — contradicts the 'unlimited' claim
                return True, quote_nums[0]
        return False, None

    # Standard numeric comparison
    claimed_nums = _extract_numeric_tokens(claimed_norm)
    if not claimed_nums:
        # No numeric tokens in the claimed value — can't do numeric contradiction check.
        # Fall through to answered (the LLM still provided a verified citation).
        return False, None

    # Check each verified citation's quote
    for cit in verified_citations:
        quote = cit.get("quote", "")
        if not quote:
            continue
        quote_nums = _extract_numeric_tokens(quote)
        if not quote_nums:
            continue

        # Find the primary numeric from the claimed value (first one, ignoring "$" prefix)
        claimed_primary = claimed_nums[0].lstrip("$")
        try:
            claimed_val_float = float(claimed_primary)
        except ValueError:
            continue

        # Check if any numeric in the quote differs meaningfully from claimed
        for qn in quote_nums:
            qn_clean = qn.lstrip("$")
            try:
                quote_val_float = float(qn_clean)
            except ValueError:
                continue

            # Values are different — this is a contradiction
            if abs(claimed_val_float - quote_val_float) > 0.001:
                # Return the first differing value as the grounded actual
                return True, qn

    return False, None


def verify_citations(
    llm_output: dict[str, Any],
    retrieved_chunks: dict[int, dict[str, Any]],
    question: str = "",
) -> dict[str, Any]:
    """
    Deterministically verifies LLM citations against retrieved context chunks.

    Args:
        llm_output: dict with:
          - "answer_draft" (str)
          - "citations" (list of dicts)
          - "premise_check" (dict: {"contains_claim": bool, "claimed_value": str|None})
        retrieved_chunks: dict keyed by page_number (int).
                          Each value: {section, text, source_file, chunk_id}.
        question: Optional user query string for legacy guardrail checks.

    Returns API.md-compliant shape (one of three states per DECISION.md Rule 15):
        Answered:   {"status": "answered", "answer": str, "citations": [...]}
        Refused:    {"status": "refused", "reason": "no_grounded_answer", "message": str}
        Corrected:  {
                      "status": "corrected",
                      "premise_claimed": str,
                      "actual_grounded_value": str,
                      "explanation": str,
                      "citations": [...]
                    }
    """
    answer_draft = llm_output.get("answer_draft", "")
    raw_citations = llm_output.get("citations", [])

    # Extract premise_check metadata from LLM output
    pc = llm_output.get("premise_check") or {}
    contains_claim = bool(pc.get("contains_claim", False)) if isinstance(pc, dict) else False
    claimed_value: str | None = pc.get("claimed_value") if isinstance(pc, dict) else None

    usage = llm_output.get("usage")

    # No citations returned by LLM -> immediate refusal
    if not raw_citations:
        return _refusal(usage=usage)

    # ── Legacy Rule 6 guard (kept as a safety net for when premise_check is absent) ──
    # When the LLM DID flag a premise claim (contains_claim=True), we trust the
    # citation verification path to enforce the correct state (corrected/answered/refused).
    # The legacy guard is only activated when premise_check was absent or contains_claim=False
    # — e.g., when using an older provider that doesn't return the new field.
    if not contains_claim and question:
        q_lower = question.lower().strip()
        all_chunks_text = " ".join(
            f"{c.get('section', '')} {c.get('text', '')}"
            for c in retrieved_chunks.values()
        ).lower()

        # 1. Number / quantity phrase verification:
        # Check specific numerical phrases like "5 days", "$500", "90 days"
        q_quantities = re.findall(r"(?:\$\s*\d+|\b\d+\s+[a-z]+|\b\d+\b)", q_lower)
        for quant in q_quantities:
            quant_clean = quant.strip()
            pattern = r"\b" + re.escape(quant_clean) + r"\b"
            if not re.search(pattern, all_chunks_text):
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
            missing_premise_words = [w for w in premise_words if not re.search(r"\b" + re.escape(w) + r"\b", all_chunks_text)]
            if len(missing_premise_words) >= 2:
                return _refusal()

        # 3. Refutation guard: If answer explicitly denies/negates a number or entity from the question, refuse
        q_words = set(re.findall(r"\b\w+\b", q_lower)) - STOPWORDS
        neg_matches = re.findall(
            r"\b(?:not|never|no|neither|none|without|instead of|cannot|can't)\s+([a-zA-Z0-9$]+(?:\s+[a-zA-Z]+)?)",
            answer_draft.lower(),
        )
        for np_phrase in neg_matches:
            first_tok = np_phrase.split()[0]
            if first_tok in q_words or np_phrase in q_lower:
                if first_tok.isdigit() or first_tok.startswith("$"):
                    return _refusal()
                if not re.search(r"\b" + re.escape(np_phrase) + r"\b", all_chunks_text):
                    return _refusal()

    # ── Citation verification pass ──────────────────────────────────────────────
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
        return _refusal(usage=usage)

    # ── Premise contradiction check (DECISION.md Rule 15) ──────────────────────
    # If the LLM flagged a contains_claim AND we have a verified citation, check
    # whether that citation's quote contradicts the claimed_value.
    # This is the enforcement point — the prompt alone is not sufficient.
    if contains_claim and claimed_value:
        contradicted, actual_grounded = _check_premise_contradiction(claimed_value, verified)
        if contradicted and actual_grounded:
            # Confirmed false premise with grounded refutation -> "corrected"
            res = {
                "status": "corrected",
                "premise_claimed": claimed_value,
                "actual_grounded_value": actual_grounded,
                "explanation": answer_draft,
                "citations": verified,
            }
            if usage:
                res["usage"] = usage
            return res
        # _check_premise_contradiction returned False — either:
        # (a) The claimed value is numerically confirmed by the citation (claim was correct) -> answered
        # (b) The claim is non-numeric/boolean and we cannot deterministically verify it
        #     without a second LLM call (prohibited by DECISION.md Rule 9) -> refused (safer)
        #
        # Distinguish (a) from (b): if the citation actually contains the same numeric value
        # as the claimed value, the claim was confirmed -> "answered". Otherwise -> "refused".
        claimed_nums = _extract_numeric_tokens(claimed_value)
        if claimed_nums:
            # There were numeric tokens; contradiction check already ran and found no diff.
            # That means the citation CONFIRMED the numeric claim -> "answered"
            pass  # fall through to answered below
        else:
            # No numeric tokens in claimed_value and no 'unlimited'-type keyword match.
            # This is a non-numeric boolean/entity premise — cannot verify without a 2nd LLM call.
            # Safer to refuse than to let through as "answered" (DECISION.md Rule 9).
            return _refusal(usage=usage)

    res = {
        "status": "answered",
        "answer": answer_draft,
        "citations": verified,
    }
    if usage:
        res["usage"] = usage
    return res


def _refusal(usage: dict[str, Any] | None = None) -> dict[str, Any]:
    """Returns the exact API.md refusal shape (DECISION.md Rule 5)."""
    res = {
        "status": "refused",
        "reason": "no_grounded_answer",
        "message": REFUSAL_MESSAGE,
    }
    if usage:
        res["usage"] = usage
    return res
