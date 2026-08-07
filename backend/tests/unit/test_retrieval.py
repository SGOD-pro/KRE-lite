"""
tests/unit/test_retrieval.py — RULES.md "Retrieval Sanity Tests".

10 factual questions from sample_doc.pdf. Each answer must appear in
the top-5 BM25+vector fused results (Recall@5 sanity check).

RULES.md requirement:
  - test_known_answer_retrieved_in_top_5 (parametrized over 10 questions)

The fixture PDF content matches tests/fixtures/create_fixture_pdf.py:
  Page 1 — Executive Summary
  Page 2 — Section 1: Leave Policy (20 days annual leave, 14 days notice, etc.)
  Page 3 — Section 2: Remote Work Policy (3 days/week, core hours 10-16)
  Page 4 — Section 3: Code of Conduct (harassment prohibited, $50 gifts, etc.)
  Page 5 — Section 4.2: Termination and Resignation (30 days notice, garden leave)
"""
from pathlib import Path

import pytest

FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "sample_doc.pdf"

# (question, expected_page_number)
# These match the fixture PDF content exactly.
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
    """
    Ingest the fixture PDF once before all retrieval tests.
    Uses an isolated Chroma dir to avoid polluting production data.
    """
    if not FIXTURE_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {FIXTURE_PDF}")

    import os
    import tempfile

    # Use a temp chroma dir so retrieval tests are isolated
    tmp_chroma = tempfile.mkdtemp(prefix="chroma_test_")

    # Monkey-patch the store's CHROMA_PERSIST_DIR for this test session
    import app.ingest.store as store_module
    original_dir = store_module.CHROMA_PERSIST_DIR
    store_module.CHROMA_PERSIST_DIR = tmp_chroma

    from app.ingest.chunker import chunk_document
    from app.ingest.store import add_chunks, reset_collection
    from app.query.bm25_retriever import invalidate_index

    reset_collection()
    invalidate_index()

    chunks = chunk_document(str(FIXTURE_PDF))
    add_chunks(chunks)
    invalidate_index()

    yield

    # Teardown — restore and clean up
    invalidate_index()
    reset_collection()
    store_module.CHROMA_PERSIST_DIR = original_dir

    import shutil
    shutil.rmtree(tmp_chroma, ignore_errors=True)


@pytest.mark.parametrize("question,expected_page", KNOWN_ANSWER_QUESTIONS)
def test_known_answer_retrieved_in_top_5(question, expected_page):
    """
    RULES.md: test_known_answer_retrieved_in_top_5

    For each factual question, the chunk containing the answer must
    appear in the top-5 results from BM25+vector fusion.
    """
    from app.query.bm25_retriever import bm25_search
    from app.query.vector_retriever import vector_search
    from app.query.fusion import reciprocal_rank_fusion

    bm25_results = bm25_search(question, top_k=20)
    vector_results = vector_search(question, top_k=20)
    fused = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)

    found_pages = [r["page_number"] for r in fused]
    assert expected_page in found_pages, (
        f"Expected page {expected_page} not in top-5 for: '{question}'\n"
        f"Got pages: {found_pages}\n"
        f"BM25 pages: {[r['page_number'] for r in bm25_results[:5]]}\n"
        f"Vector pages: {[r['page_number'] for r in vector_results[:5]]}"
    )
