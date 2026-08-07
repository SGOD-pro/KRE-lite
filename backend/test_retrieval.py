"""
test_retrieval.py — RULES.md "Retrieval Sanity Tests".

10 hand-written factual questions from sample_doc.pdf.
Each must appear in the top-5 BM25+vector results.

Expected pages are based on the fixture PDF created by
tests/fixtures/create_fixture_pdf.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest

FIXTURE_PDF = Path(__file__).parent / "tests" / "fixtures" / "sample_doc.pdf"

# (question, expected_page_number)
# These match the content in create_fixture_pdf.py
KNOWN_ANSWER_QUESTIONS = [
    ("How many days of annual leave are employees entitled to?", 2),
    ("What is the required notice period for resignation?", 5),
    ("How many days in advance must leave be approved?", 2),
    ("How many days can unused leave be carried forward?", 2),
    ("How many days per week can employees work remotely?", 3),
    ("What are the core hours for remote workers?", 3),
    ("How long is maternity leave?", 2),
    ("What is prohibited under the code of conduct?", 4),
    ("What must employees do with gifts exceeding $50?", 4),
    ("Can the company place employees on garden leave?", 5),
]


@pytest.fixture(scope="module", autouse=True)
def ingest_fixture_pdf():
    """Ingest the fixture PDF once before running retrieval tests."""
    if not FIXTURE_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {FIXTURE_PDF}. Run create_fixture_pdf.py first.")

    from app.ingest.chunker import chunk_document
    from app.ingest.store import add_chunks, reset_collection
    from app.query.bm25_retriever import invalidate_index

    reset_collection()
    invalidate_index()
    chunks = chunk_document(str(FIXTURE_PDF))
    add_chunks(chunks)
    invalidate_index()


@pytest.mark.parametrize("question,expected_page", KNOWN_ANSWER_QUESTIONS)
def test_known_answer_retrieved_in_top_5(question, expected_page):
    from app.query.bm25_retriever import bm25_search
    from app.query.vector_retriever import vector_search
    from app.query.fusion import reciprocal_rank_fusion

    bm25_results = bm25_search(question, top_k=20)
    vector_results = vector_search(question, top_k=20)
    
    fused_results = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)

    found_pages = [r["page_number"] for r in fused_results]
    assert expected_page in found_pages, (
        f"Expected page {expected_page} not in top-5 for: '{question}'. "
        f"Got pages: {found_pages}"
    )
