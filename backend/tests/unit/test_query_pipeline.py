"""
tests/unit/test_query_pipeline.py — Tests positive query answering and citation grounding.

Verifies that valid, grounded questions return status="answered", with correct answers
and valid, verified citations containing page, section, quote, and chunk_id.
"""
from pathlib import Path
import pytest

from app.query.planner import answer_question

FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "sample_doc.pdf"
TEST_SESSION_ID = "test_positive_session"


@pytest.fixture(scope="module", autouse=True)
def setup_corpus():
    """Ingests fixture PDF for positive query tests."""
    from app.ingest.chunker import chunk_document
    from app.ingest.store import add_chunks, reset_collection
    from app.query.bm25_retriever import invalidate_index

    reset_collection(session_id=TEST_SESSION_ID)
    invalidate_index()

    chunks = chunk_document(str(FIXTURE_PDF))
    add_chunks(chunks, session_id=TEST_SESSION_ID)
    invalidate_index()

    yield

    invalidate_index()
    reset_collection(session_id=TEST_SESSION_ID)


def test_positive_query_annual_leave():
    """Valid question about annual leave must be answered with verified citations."""
    result = answer_question(
        "How many days of annual leave are employees entitled to per year?",
        session_id=TEST_SESSION_ID,
    )
    assert result["status"] == "answered"
    assert "20" in result["answer"] or "twenty" in result["answer"].lower()
    assert len(result["citations"]) > 0

    citation = result["citations"][0]
    assert citation["page"] == 2
    assert "Leave Policy" in citation["section"]
    assert "20 days" in citation["quote"] or "annual leave" in citation["quote"].lower()
    assert "chunk_id" in citation


def test_positive_query_remote_work_core_hours():
    """Valid question about remote work core hours must be answered with citations."""
    result = answer_question(
        "What are the core hours during remote work days?",
        session_id=TEST_SESSION_ID,
    )
    assert result["status"] == "answered"
    assert "10:00" in result["answer"] or "16:00" in result["answer"]
    assert len(result["citations"]) > 0

    citation = result["citations"][0]
    assert citation["page"] == 3
    assert "Remote Work" in citation["section"]
    assert "10:00 to 16:00" in citation["quote"]


def test_positive_query_resignation_notice():
    """Valid question about resignation notice period must be answered with citations."""
    result = answer_question(
        "What is the required notice period for resignation?",
        session_id=TEST_SESSION_ID,
    )
    assert result["status"] == "answered"
    assert "30" in result["answer"] or "thirty" in result["answer"].lower()
    assert len(result["citations"]) > 0

    citation = result["citations"][0]
    assert citation["page"] == 5
    assert "Termination" in citation["section"]
    assert "30 days" in citation["quote"]
