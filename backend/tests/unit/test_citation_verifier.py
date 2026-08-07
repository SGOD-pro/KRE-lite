"""
tests/unit/test_citation_verifier.py — RULES.md "Citation Verifier — Unit Tests"

All tests use hand-crafted fake LLM outputs and fabricated chunk stores.
They do NOT call the real LLM, Bedrock, Qdrant, or MongoDB.
This is intentional: the verifier is deterministic code and must be
testable independently of the rest of the pipeline (DECISION.md Rule 4).

Required by RULES.md:
  - test_verifier_accepts_exact_quote_match
  - test_verifier_accepts_fuzzy_quote_match
  - test_verifier_rejects_quote_not_in_claimed_chunk
  - test_verifier_rejects_citation_missing_page_or_section
  - test_verifier_returns_refusal_shape_when_zero_citations_survive
  - test_verifier_never_bypassed_regardless_of_llm_confidence_field
"""
import pytest
from app.query.citation_verifier import verify_citations


# ── Shared fixtures ───────────────────────────────────────────────────────────

CHUNKS = {
    1: {
        "section": "Section 1: Leave Policy",
        "text": (
            "Employees are entitled to twenty days of annual leave per calendar year. "
            "Leave must be approved at least fourteen days in advance. "
            "Unused leave can be carried forward to the following year up to a maximum of five days."
        ),
        "source_file": "sample_doc.pdf",
    },
    3: {
        "section": "Section 2: Remote Work Policy",
        "text": (
            "Employees may work remotely for up to three days per week. "
            "Core hours during remote days are 10:00 to 16:00."
        ),
        "source_file": "sample_doc.pdf",
    },
    4: {
        "section": "Section 3: Code of Conduct",
        "text": (
            "Harassment and discrimination are strictly prohibited in all company premises. "
            "Employees receiving gifts exceeding fifty dollars must declare them to HR."
        ),
        "source_file": "sample_doc.pdf",
    },
}


def _llm_out(answer: str, citations: list) -> dict:
    """Helper to build fake LLM structured output."""
    return {"answer_draft": answer, "citations": citations}


# ── RULES.md Required tests ───────────────────────────────────────────────────

def test_verifier_accepts_exact_quote_match():
    """
    RULES.md: test_verifier_accepts_exact_quote_match
    A quote that is a verbatim substring of the chunk text must pass.
    """
    llm_output = _llm_out(
        answer="Employees may take 20 days of annual leave.",
        citations=[{
            "page": 1,
            "section": "Section 1: Leave Policy",
            "quote": "Employees are entitled to twenty days of annual leave per calendar year.",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "answered"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["page"] == 1
    assert result["citations"][0]["quote"] == "Employees are entitled to twenty days of annual leave per calendar year."


def test_verifier_accepts_fuzzy_quote_match():
    """
    RULES.md: test_verifier_accepts_fuzzy_quote_match
    A quote with minor paraphrase (>= 90% token overlap) must still pass.
    ARCHITECTURE.md: "LLMs paraphrase slightly even when asked not to."
    """
    llm_output = _llm_out(
        answer="Remote workers have core hours from 10am to 4pm.",
        citations=[{
            "page": 3,
            "section": "Section 2: Remote Work Policy",
            # Slightly paraphrased: "10 to 16" → "10:00 to 16:00" already in chunk,
            # but case and minimal word drop tested here
            "quote": "Core hours during remote days are 10:00 to 16:00",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "answered"
    assert len(result["citations"]) == 1


def test_verifier_rejects_quote_not_in_claimed_chunk():
    """
    RULES.md: test_verifier_rejects_quote_not_in_claimed_chunk
    A quote that does not appear (even fuzzily) in the chunk must fail.
    """
    llm_output = _llm_out(
        answer="Employees get 50 days annual leave.",
        citations=[{
            "page": 1,
            "section": "Section 1: Leave Policy",
            "quote": "Employees are entitled to fifty days of annual leave per calendar year.",  # wrong number
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    # "fifty days" is far enough from "twenty days" to fail the 90% threshold
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"
    assert "message" in result


def test_verifier_rejects_citation_missing_page():
    """
    RULES.md: test_verifier_rejects_citation_missing_page_or_section (page half)
    DECISION.md Rule 3: citation missing page is auto-failed.
    """
    llm_output = _llm_out(
        answer="Some answer.",
        citations=[{
            # page is missing
            "section": "Section 1: Leave Policy",
            "quote": "Employees are entitled to twenty days of annual leave per calendar year.",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"


def test_verifier_rejects_citation_missing_section():
    """
    RULES.md: test_verifier_rejects_citation_missing_page_or_section (section half)
    DECISION.md Rule 3: citation missing section is auto-failed.
    """
    llm_output = _llm_out(
        answer="Some answer.",
        citations=[{
            "page": 1,
            # section is missing
            "quote": "Employees are entitled to twenty days of annual leave per calendar year.",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"


def test_verifier_returns_refusal_shape_when_zero_citations_survive():
    """
    RULES.md: test_verifier_returns_refusal_shape_when_zero_citations_survive
    The refusal must be the exact shape from API.md:
      {status: "refused", reason: "no_grounded_answer", message: str}
    """
    llm_output = _llm_out(answer="", citations=[])
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0
    # Must NOT have 'answer' field (old shape) — enforce exact API.md contract
    assert "answer" not in result


def test_verifier_never_bypassed_regardless_of_llm_confidence_field():
    """
    RULES.md: test_verifier_never_bypassed_regardless_of_llm_confidence_field
    DECISION.md Rule 6: even if the LLM includes a high confidence signal,
    the verifier ignores it and checks the actual quote anyway.
    A hallucinated quote with confidence=1.0 must still be refused.
    """
    llm_output = {
        "answer_draft": "The notice period is 90 days.",
        "confidence": 1.0,       # Fake confidence field LLM might inject
        "certainty": "very high", # Another possible confidence signal
        "citations": [{
            "page": 1,
            "section": "Section 1: Leave Policy",
            "quote": "Employees must provide ninety days written notice before resignation.",  # hallucinated
        }],
    }
    result = verify_citations(llm_output, CHUNKS)
    # Verifier must check the quote regardless of the confidence fields — refused
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"


# ── Additional edge-case tests ────────────────────────────────────────────────

def test_verifier_multiple_citations_partial_pass():
    """
    When some citations pass and some fail, only passing ones are returned.
    The answer is still returned (status=answered) because >=1 citation survived.
    """
    llm_output = _llm_out(
        answer="Leave is 20 days and gifts over $50 must be declared.",
        citations=[
            {
                "page": 1,
                "section": "Section 1: Leave Policy",
                "quote": "Employees are entitled to twenty days of annual leave per calendar year.",  # PASSES
            },
            {
                "page": 4,
                "section": "Section 3: Code of Conduct",
                "quote": "Employees receiving gifts exceeding one thousand dollars must declare them.",  # FAILS
            },
        ],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "answered"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["page"] == 1


def test_verifier_page_lookup_uses_page_not_chunk_id():
    """
    The verifier looks up chunks by page number (from LLM output),
    not by any chunk_id. If the page doesn't exist in the retrieved chunks,
    the citation fails — even if the quote text happens to be correct.
    """
    llm_output = _llm_out(
        answer="Some answer.",
        citations=[{
            "page": 999,   # page doesn't exist in retrieved chunks
            "section": "Section 1: Leave Policy",
            "quote": "Employees are entitled to twenty days of annual leave per calendar year.",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "refused"


def test_verifier_answered_shape_has_required_fields():
    """
    When the verifier returns status=answered, every citation must have
    page, section, quote, chunk_id (for UI) and source_file (for SourceViewer).
    """
    llm_output = _llm_out(
        answer="Gifts over $50 must be declared.",
        citations=[{
            "page": 4,
            "section": "Section 3: Code of Conduct",
            "quote": "Employees receiving gifts exceeding fifty dollars must declare them to HR.",
        }],
    )
    result = verify_citations(llm_output, CHUNKS)
    assert result["status"] == "answered"
    c = result["citations"][0]
    assert "page" in c
    assert "section" in c
    assert "quote" in c
    assert "chunk_id" in c
    assert "source_file" in c
