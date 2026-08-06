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

## The Adversarial "Should Refuse" Test Set — THIS IS THE DEMO

Generate via the `adversarial-refusal-test-generator` skill
(AGENT.md), 15-20 questions, categories:

1. **Adjacent-but-absent facts** — asks about something plausible
   given the document's domain but never actually stated (e.g. if
   the doc covers Q3 revenue, ask about Q4 revenue).
2. **Wrong entity swap** — take a real answerable question and swap
   a correct name/number for a similar-sounding wrong one, ask if
   the wrong one is correct.
3. **Out-of-corpus questions** — ask about a real-world fact adjacent
   to the topic but never in the uploaded documents at all.
4. **Leading questions** — phrase the question to imply a false
   premise as if it were fact, see if the agent corrects or refuses
   rather than going along with the premise.

Exit criteria: **100% of this set produces a refusal, not a
fabricated answer.** This number is the one you say out loud to the
judges. If it's not 100%, you do not have a working core product yet
— this is a blocking bug, not a "nice to improve" metric.

- `test_adversarial_set_all_refuse` (parametrized over the full set,
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
