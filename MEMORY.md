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

**Phase:** Phase 3 in progress (Frontend UI implementation)
**Hour mark (approx, since build start):** 16
**Last updated:** 2026-08-07T12:05
**Last updated by:** Antigravity

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [x] Phase 1 — Ingestion + Retrieval (MongoDB Atlas + Qdrant Cloud + RRF hybrid search)
- [x] Phase 2 — Generation + Citation Verifier (Bedrock Nova + rapidfuzz verifier + pre/post guardrails)
- [ ] Phase 3 — Frontend
- [ ] Phase 4 — Polish, Docs, Demo Prep
- [ ] Buffer hours used for: [nothing yet / describe]

## Decisions Made (append-only — never delete an old entry, strike through if superseded and say why)

- [Hour 0] Pivoted architecture from local minimum viable RAG to an enterprise cloud stack (AWS Bedrock, RDS, ElastiCache) and a frontend using Vite, React, Tailwind v4, and shadcn.
- [Hour 1] Scaffolded backend and frontend in their respective folders (`backend/` and `frontend/`). Configured Vite with Tailwind v4, React Router DOM, and shadcn init.
- ~~[Hour 2] Replaced ChromaDB with RDS PostgreSQL + pgvector.~~ (Superseded)
- [Hour 8] Migrated DB architecture to MongoDB Atlas (metadata + BM25 keyword search) and Qdrant Cloud (embeddings). Removed PostgreSQL/RDS completely.
- [Hour 14] Phase 1 completed: Hybrid retrieval combining Qdrant semantic search + MongoDB `$search` BM25 via Reciprocal Rank Fusion (RRF). 10/10 retrieval tests passed.
- [Hour 15] Phase 2 completed: Integrated AWS Bedrock Nova for structured LLM generation and built `citation_verifier.py` with `rapidfuzz` (80% partial ratio). Added pre-generation guardrail (Qdrant score < 0.3 short-circuits to refusal). 9/9 citation verifier tests passed.

## Known Issues / Open Risks (things the next session needs to know about even if they're not blocking)

- `python-multipart` was missing from requirements — discovered during API test and fixed.
- Deprecation warning: FastAPI TestClient says to use `httpx2` instead of `httpx`. Harmless for now — do not fix until Phase 4 polish, it does not break tests.

## What NOT To Redo

- Do NOT re-introduce PostgreSQL/RDS or pgvector. Primary DB is MongoDB Atlas, Vector DB is Qdrant Cloud.

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): **9/9 PASSING** ✅
- Ingestion tests: **7/7 PASSING** ✅
- API endpoint tests: **6/6 PASSING** ✅
- Retrieval sanity tests: **10/10 PASSING** ✅
- Adversarial refusal set: Skipped/Pending real questions
- Playwright e2e: not written yet (Phase 3)
- CI pipeline: All core backend tests green locally ✅

## Next Session Should Start By

Start Phase 3 Frontend implementation: build the 2-pane UI matching `DESIGN.md` theme and layout in `frontend/`. Connect `POST /ingest` and `POST /query`.
