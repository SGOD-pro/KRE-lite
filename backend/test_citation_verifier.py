"""
Unit tests for citation_verifier.py — DECISION.md Rules 3, 4, 5, 6, 9.

These tests use hand-crafted fake LLM outputs against fake source
chunks. They must pass BEFORE citation_verifier.py is wired into the
full pipeline (PROMPTS.md PROMPT 2 instructs building it in this
order deliberately).

Implement `verify_citations` in app/query/citation_verifier.py with
this signature (adjust import path if your module layout differs):

    def verify_citations(
        llm_output: dict,      # {"answer_draft": str, "citations": [...]}
        retrieved_chunks: dict # {chunk_id: {"page": int, "section": str, "text": str}}
    ) -> dict:
        # returns either:
        #   {"status": "answered", "answer": str, "citations": [...]}
        # or:
        #   {"status": "refused", "reason": "no_grounded_answer", "message": str}
        ...
"""
import pytest

from app.query.citation_verifier import verify_citations


FAKE_CHUNK = {
    "doc1_chunk_0038": {
        "page": 12,
        "section": "Section 4.2 — Termination and Resignation",
        "text": (
            "In the event of resignation, employees must provide a "
            "minimum of 30 days written notice to their manager and "
            "to HR before their last working day."
        ),
    }
}


def test_verifier_accepts_exact_quote_match():
    llm_output = {
        "answer_draft": "The notice period is 30 days.",
        "citations": [
            {
                "page": 12,
                "section": "Section 4.2 — Termination and Resignation",
                "quote": "employees must provide a minimum of 30 days written notice",
                "chunk_id": "doc1_chunk_0038",
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "answered"
    assert len(result["citations"]) == 1


def test_verifier_accepts_fuzzy_quote_match():
    # Minor paraphrase of the real chunk text — should still pass at
    # the >=90% token overlap threshold specified in ARCHITECTURE.md.
    llm_output = {
        "answer_draft": "The notice period is 30 days.",
        "citations": [
            {
                "page": 12,
                "section": "Section 4.2 — Termination and Resignation",
                "quote": "employees must provide at least 30 days of written notice",
                "chunk_id": "doc1_chunk_0038",
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "answered"


def test_verifier_rejects_quote_not_in_claimed_chunk():
    llm_output = {
        "answer_draft": "The notice period is 90 days.",
        "citations": [
            {
                "page": 12,
                "section": "Section 4.2 — Termination and Resignation",
                # This text does not appear anywhere in FAKE_CHUNK.
                "quote": "employees must provide 90 days written notice",
                "chunk_id": "doc1_chunk_0038",
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "refused"
    assert result["reason"] == "no_grounded_answer"


def test_verifier_rejects_citation_missing_page_or_section():
    llm_output = {
        "answer_draft": "The notice period is 30 days.",
        "citations": [
            {
                # page missing entirely
                "section": "Section 4.2 — Termination and Resignation",
                "quote": "employees must provide a minimum of 30 days written notice",
                "chunk_id": "doc1_chunk_0038",
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "refused"


def test_verifier_returns_refusal_shape_when_zero_citations_survive():
    llm_output = {
        "answer_draft": "I think the notice period might be 30 days.",
        "citations": [],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "refused"
    assert "message" in result
    assert result["reason"] == "no_grounded_answer"


def test_verifier_never_bypassed_regardless_of_llm_confidence_field():
    # Even if the LLM output includes a confidence/certainty signal,
    # the verifier must check the actual quote text, not trust the
    # signal. DECISION.md Rule 6 — no answering from general
    # knowledge, no matter how confident the model claims to be.
    llm_output = {
        "answer_draft": "The notice period is definitely 90 days.",
        "confidence": "very_high",  # verifier must ignore this field
        "citations": [
            {
                "page": 12,
                "section": "Section 4.2 — Termination and Resignation",
                "quote": "employees must provide 90 days written notice",
                "chunk_id": "doc1_chunk_0038",
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "refused", (
        "Verifier must reject based on quote mismatch even when the "
        "LLM output claims high confidence."
    )


@pytest.mark.parametrize(
    "bad_chunk_id",
    ["doc1_chunk_9999", "", None],
)
def test_verifier_rejects_citation_referencing_unknown_chunk(bad_chunk_id):
    llm_output = {
        "answer_draft": "The notice period is 30 days.",
        "citations": [
            {
                "page": 12,
                "section": "Section 4.2 — Termination and Resignation",
                "quote": "employees must provide a minimum of 30 days written notice",
                "chunk_id": bad_chunk_id,
            }
        ],
    }
    result = verify_citations(llm_output, FAKE_CHUNK)
    assert result["status"] == "refused"
