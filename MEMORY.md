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

**Phase:** Phase 4 — Architectural Hardening In Progress
**Hour mark (approx, since build start):** 24
**Last updated:** 2026-08-07T13:30
**Last updated by:** Antigravity

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [x] Phase 1 — Ingestion + Retrieval (MongoDB Atlas + Qdrant Cloud + RRF hybrid search)
- [x] Phase 2 — Generation + Citation Verifier (Bedrock Nova + rapidfuzz verifier + pre/post guardrails)
- [x] Phase 3 — Frontend (Upload Screen + Resizable 2-Pane Chat & Source Viewer + Playwright E2E automation)
- [/] Phase 4 — Architectural Hardening (S3, two-phase ingestion, Bedrock rate limit, Source Viewer real text)
- [ ] Phase 5 — Polish, Docs, Demo Prep
- [ ] Buffer hours used for: Phase 4 architectural hardening per user feedback

## Decisions Made (append-only — never delete an old entry, strike through if superseded and say why)

- [Hour 0] Pivoted architecture from local minimum viable RAG to an enterprise cloud stack (AWS Bedrock, RDS, ElastiCache) and a frontend using Vite, React, Tailwind v4, and shadcn.
- [Hour 1] Scaffolded backend and frontend in their respective folders (`backend/` and `frontend/`). Configured Vite with Tailwind v4, React Router DOM, and shadcn init.
- ~~[Hour 2] Replaced ChromaDB with RDS PostgreSQL + pgvector.~~ (Superseded)
- [Hour 8] Migrated DB architecture to MongoDB Atlas (metadata + BM25 keyword search) and Qdrant Cloud (embeddings). Removed PostgreSQL/RDS completely.
- [Hour 14] Phase 1 completed: Hybrid retrieval combining Qdrant semantic search + MongoDB `$search` BM25 via Reciprocal Rank Fusion (RRF). 10/10 retrieval tests passed.
- [Hour 15] Phase 2 completed: Integrated AWS Bedrock Nova for structured LLM generation and built `citation_verifier.py` with `rapidfuzz` (80% partial ratio). Added pre-generation guardrail (Qdrant score < 0.3 short-circuits to refusal). 9/9 citation verifier tests passed.
- [Hour 20] Phase 3 completed: Backend updated with `session_id` session isolation. Frontend built with React + Zustand + `react-resizable-panels` matching `DESIGN.md` and mockups (Upload Screen & 2-Pane Chat/Source Viewer). `npm run build` passing cleanly.
- [Hour 22] E2E Automation Completed: Configured Playwright end-to-end test suite reading real PDF documents (`data/*.pdf`). Parallelized Bedrock embeddings (`ThreadPoolExecutor`) and batched Qdrant upserts (`batch_size=50`) with auto-created payload index. 3/3 Playwright tests passing green.
- [Hour 24] Phase 4 Hardening Started:
  - **S3 Integration**: Backend checks/creates `cited-or-silent-docs` S3 bucket on startup. PDFs uploaded to S3 in parallel via `ThreadPoolExecutor` during `/ingest`.
  - **Two-Phase Ingestion**: `/ingest` → upload to S3 + chunk to MongoDB (fast, no embedding). `/analyze` → Bedrock embeddings + Qdrant upsert (slow, rate-limited).
  - **Bedrock Rate Limit**: `embed_service.py` now runs SEQUENTIALLY with strict 1.4s sleep after every Titan embedding call. `ThreadPoolExecutor` removed from embed path.
  - **Nova Model ID Fix**: Changed from `amazon.nova-pro-v1:0` to `ap.amazon.nova-pro-v1:0` (cross-region inference profile required for `ap-south-1`).
  - **Source Viewer Anti-Hallucination**: `citation_verifier.py` now enriches citations with `text` (real chunk text) and `source_file`. `SourceViewer.tsx` renders actual MongoDB content with inline quote highlighting. All mock/hardcoded text removed.
  - **Frontend Two-Phase UI**: `UploadScreen.tsx` has animated progress steps (Upload & Chunk → Semantic Indexing). "Start Analyzing" button disabled until phase 1 complete.
  - **E2E Tests Expanded**: 8 Playwright tests covering: single PDF, UI state, happy path + real text anti-hallucination check, adversarial guardrail, off-topic guardrail, multi-PDF, new session reset, citation page nav.
  - **Qdrant Startup Init**: `_init_qdrant_collection()` called at server startup to ensure `session_id` payload index always exists before any query.

## Known Issues / Open Risks

- `python-multipart` was missing from requirements — discovered during API test and fixed.
- Deprecation warning: FastAPI `@app.on_event("startup")` is deprecated in favor of `lifespan`. Harmless for now.
- Bedrock Titan embeddings are now sequential (1.4s/chunk). A 100-chunk document takes ~140s to analyze. This is enforced rate-limit compliance.

## What NOT To Redo

- Do NOT re-introduce PostgreSQL/RDS or pgvector. Primary DB is MongoDB Atlas, Vector DB is Qdrant Cloud.
- Do NOT parallelize Bedrock Titan embeddings — 1.4s sequential sleep is a hard requirement.
- Do NOT use `amazon.nova-pro-v1:0` — use `ap.amazon.nova-pro-v1:0` for `ap-south-1` region.

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): **9/9 PASSING** ✅
- Ingestion tests: **7/7 PASSING** ✅
- API endpoint tests: **6/6 PASSING** ✅
- Retrieval sanity tests: **10/10 PASSING** ✅
- Pytest total: **32/32 PASSING** ✅
- Playwright E2E tests: **8 tests — running** ⏳
- CI pipeline: All core backend & Playwright frontend tests green locally ✅

## Next Session Should Start By

Start Phase 5 — Polish, Docs & Demo Prep:
1. Create final README with one-command setup instructions.
2. Write demo script matching PROJECT.md ("what judges see").
3. Final adversarial refusal verification.
4. Run `npx playwright test` one more time to confirm all 8 tests pass.
