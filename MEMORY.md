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

**Phase:** Phase 1 in progress (ingestion done, retrieval pending Bedrock/RDS wiring)
**Hour mark (approx, since build start):** 2
**Last updated:** 2026-08-07T04:30
**Last updated by:** Antigravity

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
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

- [Hour 0] Pivoted architecture from local minimum viable RAG to an enterprise cloud stack (AWS Bedrock, RDS, ElastiCache) and a frontend using Vite, React, Tailwind v4, and shadcn.
- [Hour 1] Scaffolded backend and frontend in their respective folders (`backend/` and `frontend/`). Configured Vite with Tailwind v4, React Router DOM, and shadcn init.
- [Hour 2] Replaced ChromaDB with RDS PostgreSQL + pgvector. Dropped sentence-transformers/torch/onnxruntime — all embeddings now via AWS Bedrock Titan Embed v2. Added config.py with dev/prod boto3 profile logic (dev: profile_name='aws', prod: IAM role). Region: ap-south-1. All 7 ingestion tests passing.

## Known Issues / Open Risks (things the next session needs to know
## about even if they're not blocking)

- `python-multipart` was missing from requirements — discovered during API test and fixed.
- Deprecation warning: FastAPI TestClient says to use `httpx2` instead of `httpx`. Harmless for now — do not fix until Phase 4 polish, it does not break tests.
- Retrieval tests (test_retrieval.py) are written but skip when RDS/Bedrock is not reachable. Run them once RDS endpoint + Bedrock access confirmed in ap-south-1.

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

- Unit tests (citation verifier): not written yet (Phase 2)
- Ingestion tests: **7/7 PASSING** ✅
- API endpoint tests: **6/6 PASSING** ✅ (health, 400, 422, happy-path mocked, query 503, query 400)
- Retrieval sanity tests: written, require live RDS + Bedrock (skip until env is wired)
- Adversarial refusal set: not written yet (Phase 2)
- Playwright e2e: not written yet (Phase 3)
- CI pipeline: **13/13 tests green locally** ✅; full run needs RDS+Bedrock env vars

## Next Session Should Start By

<!-- One or two sentences, written by the session that's ending, for
the session that's about to start. Be specific. -->

Next session should start Phase 1 retrieval integration: wire up test_retrieval.py against a real RDS instance with pgvector installed and real Bedrock Titan embed calls. Then move to Phase 2 (llm_service.py + citation_verifier.py). Do NOT start Phase 2 until Recall@5 on 10 retrieval questions passes.
