# MEMORY.md — Resumable Build State

**READ THIS FILE FIRST, BEFORE DOING ANYTHING ELSE, AT THE START OF
EVERY SESSION.** It tells you exactly what's done, what's in
progress, and what decisions have already been made so you don't
re-litigate them.

Update this file at the END of every session, before stopping, even
if the phase isn't complete. A stale MEMORY.md is worse than none —
it will make the next session waste time re-verifying things or
contradicting a decision already made.

---

## Current Status

**Phase:** [Phase 0 / 1 / 2 / 3 / 4 — update this]
**Hour mark (approx, since build start):** [update this]
**Last updated:** [timestamp]
**Last updated by:** [your name / agent session ID if useful]

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [ ] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [ ] Phase 1 — Ingestion + Retrieval
- [ ] Phase 2 — Generation + Citation Verifier
- [ ] Phase 3 — Frontend
- [ ] Phase 4 — Polish, Docs, Demo Prep
- [ ] Buffer hours used for: [nothing yet / describe]

## Decisions Made (append-only — never delete an old entry, strike
## it through if superseded and say why)

<!--
Example format:
- [Hour 4] Chose Chroma over sqlite-vec for vector store — faster
  to set up, no schema migration needed for a single-session demo.
- [Hour 22] Cut NVIDIA rerank per PHASES.md hour-22 rule — API key
  worked but latency was inconsistent, not worth the risk this close
  to Phase 2 exit criteria.
-->

- [Hour 0] Doc set chosen for demo: [FILL IN — filename(s), why
  chosen, page count]

## Known Issues / Open Risks (things the next session needs to know
## about even if they're not blocking)

<!--
Example:
- Citation verifier's fuzzy-match threshold (90% token overlap) may
  be too strict — 2 of 10 sanity-check questions returned refusals
  that should have answered. Needs tuning in Phase 2, not yet fixed.
-->

## What NOT To Redo

<!-- Things already tried and rejected, so the next session doesn't
waste time re-trying them. -->

<!--
Example:
- Tried Postgres+pgvector in Phase 0, reverted to Chroma — setup
  friction wasn't worth it for a single-session demo. Don't
  reintroduce it (see BOUNDARIES.md — cloud infra is explicitly cut).
-->

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): [passing / failing / not written yet]
- Ingestion tests: [passing / failing / not written yet]
- Retrieval sanity tests: [passing / failing / not written yet]
- Adversarial refusal set: [X / Y refusing correctly — this number
  matters more than any other test result, track it explicitly]
- Playwright e2e: [passing / failing / not written yet]
- CI pipeline: [green / red — if red, why, and is it blocking]

## v1.1 Status (only touch after v1 deployed + demo video recorded)

- [ ] v1 deploy confirmed working (gate — do not start v1.1 before this)
- [ ] Two-tier retrieval (page index + filtered vector search)
- [ ] Confidence scoring (cosine threshold, 3-tier)
- [ ] Token/latency metrics capture
- [ ] Context compression (regex clean)
- [ ] Auditor agent + POST /audit
- [ ] ConfidenceMeter + MetricsBar + Audit page UI
- [ ] v1 adversarial set regression check (must stay 100%)

## Next Session Should Start By

<!-- One or two sentences, written by the session that's ending, for
the session that's about to start. Be specific. -->

[FILL IN before ending each session]