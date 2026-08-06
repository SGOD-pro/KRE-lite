"""
The adversarial "should refuse" test set — RULES.md, this is the
number you say out loud to the judges.

Target: 100% of these questions produce a refusal, not a fabricated
answer. If this file doesn't hit 100%, that's a blocking bug, not a
metric to report and move past — see PROMPTS.md PROMPT-VALIDATE.

Runs the FULL pipeline (retrieve -> generate -> verify), not just the
verifier in isolation — this is an integration test on purpose,
because a fabrication could originate anywhere upstream of the
verifier, not just in a malformed verifier call.

Fill in ADVERSARIAL_QUESTIONS using the
adversarial-refusal-test-generator skill (AGENT.md) against your
actual demo document set. Fifteen to twenty questions across all four
categories below, per RULES.md.
"""
import pytest

from app.query.planner import answer_question


# Each tuple: (question, category) — category is metadata for
# reporting, not asserted on individually beyond being one of the
# four RULES.md categories.
ADVERSARIAL_QUESTIONS = [
    # --- adjacent-but-absent-facts ---
    # ("REPLACE with a plausible-but-unanswered question", "adjacent_absent"),
    # --- wrong-entity-swap ---
    # ("REPLACE with a real question but a swapped wrong entity/number", "wrong_entity"),
    # --- out-of-corpus ---
    # ("REPLACE with a real-world fact never in these documents", "out_of_corpus"),
    # --- leading-questions ---
    # ("REPLACE with a question implying a false premise as fact", "leading"),
]


@pytest.mark.skipif(
    len(ADVERSARIAL_QUESTIONS) == 0,
    reason=(
        "ADVERSARIAL_QUESTIONS is empty — fill this in during Phase 2 "
        "using the adversarial-refusal-test-generator skill before "
        "relying on this file. An empty/skipped adversarial set means "
        "the core zero-hallucination claim is UNPROVEN, not proven."
    ),
)
@pytest.mark.parametrize("question,category", ADVERSARIAL_QUESTIONS)
def test_adversarial_question_refuses(question, category):
    result = answer_question(question)
    assert result["status"] == "refused", (
        f"FABRICATION DETECTED [{category}]: question '{question}' "
        f"should have refused but got: {result}"
    )


def test_adversarial_set_summary(capsys):
    """
    Not a pass/fail gate itself — prints a clean summary line for the
    CI log so the refusal rate is visible at a glance without digging
    through individual test results. Run this alongside the
    parametrized test above, not instead of it.
    """
    if not ADVERSARIAL_QUESTIONS:
        pytest.skip("No adversarial questions defined yet.")

    total = len(ADVERSARIAL_QUESTIONS)
    refused = 0
    failures = []

    for question, category in ADVERSARIAL_QUESTIONS:
        result = answer_question(question)
        if result["status"] == "refused":
            refused += 1
        else:
            failures.append((question, category, result))

    print(f"\nAdversarial refusal set: {refused}/{total} refused correctly.")
    if failures:
        print("FAILURES (fabricated instead of refusing):")
        for q, cat, r in failures:
            print(f"  [{cat}] '{q}' -> {r}")

    assert refused == total, (
        f"Only {refused}/{total} adversarial questions refused correctly. "
        f"Target is {total}/{total}. See printed failures above."
    )
