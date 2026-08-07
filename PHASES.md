# PHASES.md — 48-Hour Build Sequence

## Rules
- Do not start Phase N+1 until Phase N exit criteria pass.
- If Phase 2 is not done by hour 20, cut the NVIDIA rerank stage
  (Rule: optional means optional — cut it, don't debug it further).
- Every phase's exit criteria include at least one test in RULES.md.
- No cloud deployment work happens before Phase 4 exit criteria pass.
  See BOUNDARIES.md.

---

## Phase 0 — Setup (Hours 0-3)

Deliverables:
- Repo scaffolded, docker-compose skeleton, FastAPI hello-world.
- AGENT.md, ARCHITECTURE.md, DECISION.md, PROJECT.md committed
  (this doc set — done before Phase 0 even starts, good).
- GitHub Actions workflow file exists (can be a no-op that just
  installs deps and runs `pytest --collect-only` — make it GREEN
  from commit one, then add real tests. A red pipeline from hour 3
  onward is a self-inflicted wound).
- Document set for the demo chosen and finalized (10-30 pages, real
  content, not lorem ipsum — pick something with clear headings so
  page/section chunking is easy).

Exit Criteria:
- `docker-compose up` starts the FastAPI app, `/health` returns 200.
- CI pipeline green on a trivial commit.

---

## Phase 1 — Ingestion + Retrieval (Hours 3-14)

Deliverables:
- chunker.py: splits by page + heading, enforces DECISION.md Rule 7
  (no chunk without page_number + section_title).
- embed_service.py: BGE-small-en-v1.5 ONNX, local.
- store.py: Chroma or sqlite-vec.
- bm25_retriever.py + vector_retriever.py.
- POST /ingest working end to end on the real demo document set.

Exit Criteria:
- All chunks from the demo doc set have non-null page_number and
  section_title — verified by test, not eyeballing.
- A known factual question retrieves the chunk that actually
  contains the answer, in the top 5 results (basic Recall@5 sanity
  check on ~10 hand-written questions, not a formal benchmark).

---

## Phase 2 — Generation + Citation Verifier (Hours 14-26)

**This phase is the actual product. Do not rush it to get to the
frontend.**

Deliverables:
- llm_service.py: single structured-output call.
- citation_verifier.py: the core guardrail (ARCHITECTURE.md).
- planner.py: wires retrieve -> generate -> verify -> respond.
- POST /query returns either a verified answer or a clean refusal.
- rerank_service.py (NVIDIA Build) — OPTIONAL. Attempt after the
  above is solid. If it's not working cleanly by hour 22, cut it and
  note the decision in ARCHITECTURE.md. Do not let an optional
  precision improvement threaten the core deliverable.

Exit Criteria:
- On the "should answer" test set (RULES.md): correct answers with
  verified citations.
- On the "should refuse" adversarial test set (RULES.md): clean
  refusals, zero fabricated answers.
- Citation verifier has its own unit tests independent of the full
  pipeline (feed it hand-crafted fake LLM outputs, confirm it
  catches bad citations).

---

## Phase 3 — Frontend (Hours 26-38)

Deliverables:
- Two-pane UI (UI-UX.md): chat + source viewer.
- Citation chips clickable, scroll-to-highlight in source viewer.
- Refusal state has a distinct, honest UI treatment (not styled like
  an error — it's a correct behavior, not a failure).
- Basic Playwright smoke test: ask a real question, see an answer
  with a citation; ask an adversarial question, see a refusal.

Exit Criteria:
- Playwright test passes in CI.
- A person who has never seen this project can run
  `docker-compose up`, open the browser, and successfully ask both
  question types without being told how.

---

## Phase 4 — Polish, Docs, Demo Prep (Hours 38-46)

Deliverables:
- README with one-command setup instructions.
- Demo script written and rehearsed (see PROJECT.md "what judges
  see").
- Demo video recorded (3 minutes) as a submission fallback in case
  live demo has issues.
- AGENTS_AND_SKILLS.md finalized documenting the custom agent + skill.
- CI pipeline green on the actual final commit, not an earlier one.

Exit Criteria:
- All non-negotiables checklist (PROJECT.md) verified present in
  repo.
- Fresh clone + docker-compose up works on a machine that hasn't
  touched this repo before (ask a teammate to try it cold).

---

## Hours 46-48 — Buffer

Do not schedule real work here. This is for the thing that breaks at
hour 44 that you didn't expect. If nothing breaks, use it to record a
cleaner demo video or write a better README. Do not use it to add
scope.

---

## Phase 5 — v1.1 (POST-DEPLOY ONLY, do not start till Phase 4 exit
## + deploy confirmed working)

Gate: v1 must be deployed + demo-video recorded FIRST. v1.1 is pure
upside, never risk v1 core to build it.

Deliverables:
- page_index table + ingest-time summary gen (cheap model)
- Tier 1 filter in retrieval path (planner.py update)
- Confidence scoring (cosine threshold, pre-LLM gate)
- Metrics capture wrap on llm_service.py
- Context compression (regex clean, pre-embed)
- auditor-agent (new module: app/audit/)
- POST /audit endpoint
- ConfidenceMeter, MetricsBar, Audit page (UI-UX.md v1.1)

Exit Criteria:
- v1's adversarial refusal set STILL 100% (regression check — v1.1
  changes retrieval path, must not break v1's core guarantee)
- Confidence tiers correctly gate: manually craft 3 queries, 1 per
  tier, confirm correct routing + 0 LLM call logged for REFUSE tier
- Audit endpoint: test doc + 3-rule ruleset, correct verdict per
  DECISION.md Rule 14 (no forced pass/fail w/o evidence)
- Metrics fields present + non-null on every "answered" response

Test Cases Required (add to RULES.md v1.1 section):
- test_confidence_tier_high_routes_correctly
- test_confidence_tier_low_routes_correctly
- test_confidence_tier_refuse_skips_llm_call (assert LLM mock not
  called)
- test_audit_rule_with_evidence_returns_pass_or_fail
- test_audit_rule_without_evidence_returns_unable_to_verify_not_forced_binary
- test_v1_adversarial_set_still_100_percent_after_v1.1_changes
- test_metrics_fields_present_on_answered_response

## Deferred to "if time remains" (never load-bearing)

- NVIDIA rerank stage, if not done by hour 22 (Phase 2 note above).
- Cloud deployment (Render/Railway/Fly) — only after Phase 4 exits
  clean. See BOUNDARIES.md for why this isn't required at all.
- Ticket-clustering-style "related questions" feature.