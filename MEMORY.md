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

**Phase:** Phase 0 — COMPLETE, Phase 1 not started
**Hour mark (approx, since build start):** ~3h (Phase 0 window)
**Last updated:** 2026-08-07T12:07:00+05:30
**Last updated by:** Antigravity agent, session cfe78a93

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [ ] Phase 1 — Ingestion + Retrieval
- [ ] Phase 2 — Generation + Citation Verifier
- [ ] Phase 3 — Frontend
- [ ] Phase 4 — Polish, Docs, Demo Prep
- [ ] Buffer hours used for: nothing yet

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

- [Phase 0] Replaced Lambda Dockerfile with python:3.13-slim + uvicorn.
  The previous Dockerfile used `public.ecr.aws/lambda/python:3.13`,
  `mangum`, and `CMD handler.handler` — all BOUNDARIES.md-violating
  (cloud deploy out of scope for Phase 0-4). The new Dockerfile is a
  plain `uvicorn app.api.main:app` server, matching ARCHITECTURE.md.

- [Phase 0] Stripped postgres+redis from docker-compose.yml. Previous
  compose had postgres+pgvector and redis services — not in the approved
  Phase 0 tech stack. ARCHITECTURE.md says vector store is local Chroma
  or sqlite-vec (no external service needed for Phase 1). These services
  were removed. They will NOT be re-added unless BOUNDARIES.md's
  "if infra time allows" condition for Postgres+pgvector is met
  (i.e. after Phase 4 exits clean).

- [Phase 0] deploy.yml disabled via `on: {}`. The CD workflow was a
  Lambda+SAM deployment pipeline. BOUNDARIES.md says cloud deployment
  is out of scope. File is preserved in git history; re-enable in
  Phase 4 if a Render/Railway deploy attempt is made.

- [Phase 0] requirements.txt uses `>=` pins, not `==`. Reason: pydantic
  2.7.0 doesn't have pre-built wheels for Python 3.13 and compiles
  pydantic-core from Rust source (very slow, CI-hostile). System already
  has pydantic 2.13.4 installed. Using >= so pip picks compatible
  pre-built wheels. Exact lock-file pinning can be done in Phase 4 with
  `pip freeze > requirements-lock.txt`.

- [Phase 0] pytest.ini sets `testpaths = tests/unit/`. The repo root has
  legacy test files (test_citation_verifier.py, test_ingestion.py, etc.)
  that import Phase 1/2 deps (boto3, qdrant_client) not installed yet.
  Pointing pytest at only `tests/unit/` keeps CI green. Those files
  will be moved/superseded in Phase 1/2 when their deps are added.

- [Phase 0] Python version: 3.13 (matches local install and docker image).
  CI uses `python-version: "3.13"`. Do not change to 3.11 or 3.12.

## Known Issues / Open Risks (things the next session needs to know
## about even if they're not blocking)

- The root-level test files (`backend/test_citation_verifier.py`,
  `backend/test_ingestion.py`, `backend/test_api.py`, etc.) exist from
  a previous session's work and import Phase 1/2 deps. They are NOT
  collected by pytest (pytest.ini points to `tests/unit/` only). In
  Phase 1, decide: move them to `tests/unit/` (preferred) OR delete
  and rewrite. Don't leave them dangling past Phase 2.

- `backend/conftest.py`, `backend/handler.py`, `backend/samconfig.toml`,
  `backend/template.yaml` are Lambda SAM artifacts from the previous
  session. They are not harmful (imports are lazy, not at module level)
  but should be cleaned up in Phase 4. handler.py and template.yaml
  can be deleted; conftest.py is fine as-is (just adds backend/ to
  sys.path).

- The `backend/app/ingest/` and `backend/app/query/` files already have
  Phase 1/2 implementation code from a previous session (chunker.py,
  embed_service.py, store.py, bm25_retriever.py, vector_retriever.py,
  citation_verifier.py, llm_service.py, planner.py). These files import
  deps that are NOT yet in requirements.txt (boto3, qdrant_client, pymupdf,
  etc.). They will become importable again once Phase 1 deps are added.
  Do NOT import from these modules until Phase 1 starts.

## What NOT To Redo

- Do NOT re-add postgres or redis to docker-compose.yml for Phase 1.
  The approved vector store is local Chroma (embedded mode, no Docker
  service needed) or sqlite-vec. Postgres+pgvector is BOUNDARIES.md-gated.

- Do NOT add `mangum` or boto3 to requirements.txt. They were there for
  the Lambda deployment model which is explicitly out of scope.

- Do NOT pin pydantic to 2.7.0 — it has no Python 3.13 wheels and will
  cause a 10+ minute source compilation on every CI run.

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): not written yet
- Ingestion tests: not written yet
- Retrieval sanity tests: not written yet
- Adversarial refusal set: not written yet
- Playwright e2e: not written yet
- CI pipeline: GREEN — 4/4 tests pass in `tests/unit/test_health.py`

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

Reading this file, then reading PHASES.md Phase 1 section. Phase 1
starts with installing Phase 1 deps (pymupdf, rank-bm25, chromadb,
onnxruntime, thefuzz) into requirements.txt and verifying the existing
`app/ingest/chunker.py` works against the chosen demo document set —
confirm every chunk has non-null `page_number` and `section_title`
before touching embed_service.py or store.py.