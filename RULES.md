# RULES.md — Required Test Cases

## Citation Verifier — Unit Tests (independent of full pipeline)

- `test_verifier_accepts_exact_quote_match`
- `test_verifier_accepts_fuzzy_quote_match` (minor paraphrase, >=90%
  token overlap still passes)
- `test_verifier_rejects_quote_not_in_claimed_chunk`
- `test_verifier_rejects_citation_missing_page_or_section`
- `test_verifier_returns_refusal_shape_when_zero_citations_survive`
- `test_verifier_never_bypassed_regardless_of_llm_confidence_field`
  (if the LLM output includes any kind of confidence/certainty
  signal, prove the verifier ignores it and checks the actual quote
  anyway — DECISION.md Rule 6)

## Ingestion Tests

- `test_every_chunk_has_page_number`
- `test_every_chunk_has_section_title`
- `test_chunk_size_within_target_range`

## Retrieval Sanity Tests (small, hand-written set — not a formal
## benchmark, just enough to catch regressions)

- 10 factual questions with known correct source chunks.
- `test_known_answer_retrieved_in_top_5` for each.

## The Adversarial Guardrail & Correction Test Set — THIS IS THE DEMO

Generate via the `adversarial-refusal-test-generator` skill
(AGENT.md), 15-20 questions, categories:

1. **Adjacent-but-absent facts** (5 questions) — asks about something plausible
   given the document's domain but never actually stated (e.g. bereavement leave, 401k match).
   *Expected outcome:* `status="refused"` (no grounding exists).
2. **Wrong entity / number swap** (5 questions) — take a real answerable question and swap
   a correct name/number for a similar-sounding wrong one, ask if the wrong one is correct
   (e.g. 45 days leave, 90 days notice, $500 gifts, 5 days remote, 12 weeks paternity).
   *Expected outcome:* `status="corrected"` (system refutes false premise with verified citation).
3. **Out-of-corpus questions** (5 questions) — ask about a real-world fact adjacent
   to the topic but never in the uploaded documents at all (e.g. Google revenue, UK Prime Minister).
   *Expected outcome:* `status="refused"` (no grounding exists).
4. **Leading questions** (4 questions) — phrase the question to imply a false
   premise as if it were fact (e.g. unlimited rollover, no VPN on Fridays, $200 gift, 60 days resignation).
   *Expected outcome:* `status="corrected"` (system refutes false premise with verified citation).

### 3-State Response Classification Note
Questions with false premises where the document contains explicit ground truth contradict the premise
and MUST produce `status="corrected"` with a verified citation showing the true value (DECISION.md Rule 15).
Questions with no grounding in the corpus MUST produce `status="refused"` (DECISION.md Rule 5).
Neither case is permitted to return `status="answered"` or fabricate an answer around the premise.

The deterministic premise-contradiction check (`_check_premise_contradiction()` in `citation_verifier.py`)
handles **numeric** contradictions only (digits and written-out number words). Boolean/entity premises
(e.g., "without using a VPN") cannot be detected without a second LLM call, which is prohibited by
DECISION.md Rule 9. For those questions, `refused` is the safe and acceptable outcome.

Exit criteria: **100% of this set produces either a clean refusal or a verified correction (0% ungrounded answering / 0% false-premise compliance).**
This is the core proof of cited-or-silent integrity:
- 12/19 questions: `status="refused"` (no corpus grounding, non-numeric boolean premise, or open-query phrasing that doesn't trigger LLM premise detection reliably)
- 7/19 questions: `status="corrected"` (grounded numeric refutation, detected reliably)
- 0/19 questions: `status="answered"`

- `test_adversarial_set_all_refuse_or_correct` (parametrized over the full 19-question set,
  CI-gating — a single failure here should fail the build)

## End-to-End (Playwright)

- `test_happy_path_question_shows_citation_and_highlights_source`
- `test_adversarial_question_shows_refusal_not_error_state`
- `test_citation_click_scrolls_and_highlights_correct_page`

## What "Green CI" Means Here

The GitHub Actions workflow must run, at minimum:
1. `pytest` (all unit + adversarial tests above)
2. Playwright suite
3. A lint/format check (keep it simple — ruff or similar)

All three block merge on failure. A red pipeline the night before
submission is worse than a smaller feature set with a green one —
this is explicit in the hackathon's own non-negotiables.
