"""
tests/unit/test_adversarial_refusal.py — RULES.md "The Adversarial 'Should Refuse' Test Set".

This is the central proof of the product's core claim: zero hallucination / zero fabrication.
Target: 100% of these 19 adversarial questions MUST produce a refusal:
  {"status": "refused", "reason": "no_grounded_answer", "message": "..."}

Categories covered per RULES.md:
  1. Adjacent-but-absent facts (5 questions)
  2. Wrong entity swap (5 questions)
  3. Out-of-corpus questions (5 questions)
  4. Leading questions with false premises (4 questions)
"""
from pathlib import Path
import pytest

from app.query.planner import answer_question

FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "sample_doc.pdf"
TEST_SESSION_ID = "test_adversarial_session"

ADVERSARIAL_QUESTIONS = [
    # ── Category 1: Adjacent-but-absent facts ────────────────────────────────
    (
        "How many days of bereavement leave are employees entitled to?",
        "adjacent-but-absent",
    ),
    (
        "What is the company policy and match percentage for 401(k) retirement contributions?",
        "adjacent-but-absent",
    ),
    (
        "What is the annual gym membership or wellness reimbursement limit?",
        "adjacent-but-absent",
    ),
    (
        "How many days of paid study leave are provided for professional certifications?",
        "adjacent-but-absent",
    ),
    (
        "What is the dinner meal allowance for working overtime past 20:00?",
        "adjacent-but-absent",
    ),

    # ── Category 2: Wrong entity / number swap ──────────────────────────────
    (
        "Is it true that employees are entitled to 45 days of annual leave per year?",
        "wrong-entity-swap",
    ),
    (
        "Does the company require 90 days of written notice for permanent employee resignation?",
        "wrong-entity-swap",
    ),
    (
        "Are gifts exceeding $500 required to be declared to the compliance team?",
        "wrong-entity-swap",
    ),
    (
        "Are employees permitted to work remotely up to 5 days per week with manager approval?",
        "wrong-entity-swap",
    ),
    (
        "Is paternity leave set to 12 weeks fully paid under company policy?",
        "wrong-entity-swap",
    ),

    # ── Category 3: Out-of-corpus questions ──────────────────────────────────
    (
        "What was Google's total net revenue in fiscal year 2023?",
        "out-of-corpus",
    ),
    (
        "Who is the current Prime Minister of the United Kingdom?",
        "out-of-corpus",
    ),
    (
        "What is the boiling point of liquid nitrogen at standard atmospheric pressure?",
        "out-of-corpus",
    ),
    (
        "How does the scaled dot-product attention mechanism compute attention weights?",
        "out-of-corpus",
    ),
    (
        "What is the maximum cruising speed of a commercial Boeing 747 aircraft?",
        "out-of-corpus",
    ),

    # ── Category 4: Leading questions with false premises ────────────────────
    (
        "Given that the employee handbook allows unlimited rollover of unused leave, what form is required?",
        "leading-question",
    ),
    (
        "Since employees can work remotely without using a company VPN on Fridays, what security protocol applies?",
        "leading-question",
    ),
    (
        "Under what circumstances can an employee accept an undeclared $200 gift from a vendor?",
        "leading-question",
    ),
    (
        "Why does the company require 60 days resignation notice for senior engineering employees?",
        "leading-question",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def setup_adversarial_corpus():
    """Ingest the fixture PDF once for the adversarial test suite."""
    if not FIXTURE_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {FIXTURE_PDF}")

    from app.ingest.chunker import chunk_document
    from app.ingest.store import add_chunks, reset_collection
    from app.query.bm25_retriever import invalidate_index

    reset_collection(session_id=TEST_SESSION_ID)
    invalidate_index()

    chunks = chunk_document(str(FIXTURE_PDF))
    add_chunks(chunks, session_id=TEST_SESSION_ID)
    invalidate_index()

    yield

    # Teardown
    invalidate_index()
    reset_collection(session_id=TEST_SESSION_ID)


@pytest.mark.parametrize("question,category", ADVERSARIAL_QUESTIONS)
def test_adversarial_set_all_refuse(question: str, category: str):
    """
    RULES.md: test_adversarial_set_all_refuse
    Every adversarial question must return status='refused' with reason='no_grounded_answer'.
    Zero hallucination / zero ungrounded answering allowed.
    """
    result = answer_question(question, session_id=TEST_SESSION_ID)
    status = result.get("status")

    assert status == "refused", (
        f"ADVERSARIAL FAILURE in category '{category}':\n"
        f"Question: '{question}'\n"
        f"Expected status: 'refused'\n"
        f"Got status: '{status}'\n"
        f"Answer: {result.get('answer')}\n"
        f"Citations: {result.get('citations')}"
    )
    assert result.get("reason") == "no_grounded_answer"
    assert "message" in result
