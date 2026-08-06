"""
Retrieval sanity tests — RULES.md "Retrieval Sanity Tests".

Not a formal benchmark. Ten hand-written factual questions, each with
a known chunk_id (or a page_number match) that must appear in the
top-5 retrieved results. Fill these in once your demo document set is
finalized (MEMORY.md "Hour 0" entry) — this file is a skeleton, not a
finished test.
"""
import pytest

from app.query.bm25_retriever import bm25_search
from app.query.vector_retriever import vector_search


# FILL IN: 10 (question, expected_page_number) pairs specific to your
# actual demo documents. Placeholder examples below — replace all of
# them before relying on this file.
KNOWN_ANSWER_QUESTIONS = [
    ("REPLACE — a real factual question", "REPLACE — expected page number"),
    # ... 9 more
]


@pytest.mark.parametrize("question,expected_page", KNOWN_ANSWER_QUESTIONS)
def test_known_answer_retrieved_in_top_5(question, expected_page):
    bm25_results = bm25_search(question, top_k=10)
    vector_results = vector_search(question, candidates=bm25_results, top_k=5)

    found_pages = [r["page_number"] for r in vector_results]
    assert expected_page in found_pages, (
        f"Expected page {expected_page} not in top-5 retrieval for "
        f"question: '{question}'. Got pages: {found_pages}"
    )
