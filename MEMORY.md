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

**Phase:** Phase 1 — COMPLETE, Phase 2 not started
**Hour mark (approx, since build start):** ~8h (Phase 0 + 1)
**Last updated:** 2026-08-07T17:50:00+05:30
**Last updated by:** Antigravity agent, session cfe78a93

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [x] Phase 1 — Ingestion + Retrieval
- [ ] Phase 2 — Generation + Citation Verifier
- [ ] Phase 3 — Frontend
- [ ] Phase 4 — Polish, Docs, Demo Prep
- [ ] Buffer hours used for: nothing yet

## Decisions Made (append-only — never delete an old entry, strike
## it through if superseded and say why)

- [Hour 0] Doc set chosen for demo: demo PDFs are in `data/`:
  - `1706.03762v7 (1).pdf` — Attention Is All You Need (transformer paper)
  - `2103.16775v1.pdf` — a longer ML paper
  - `2304.10557v6.pdf` — another ML paper
  - `2507.19595v3.pdf` — another ML paper
  All are ArXiv PDFs with clear headings and sections, well-suited for
  page + section chunking.

- [Phase 0] Replaced Lambda Dockerfile with python:3.13-slim + uvicorn.
- [Phase 0] Stripped postgres+redis from docker-compose.yml.
- [Phase 0] deploy.yml disabled via `on: {}`.
- [Phase 0] requirements.txt uses `>=` pins (no Python 3.13 pydantic-core wheel).
- [Phase 0] pytest.ini sets testpaths = tests/unit/.
- [Phase 0] Python version: 3.13.

- [Phase 1] Chose sentence-transformers (PyTorch backend) over raw ONNX
  runtime for BGE-small-en-v1.5. Reason: sentence-transformers downloads
  model weights automatically, handles tokenization correctly for BGE models
  (passage prefix), and the PyTorch backend produces identical vectors to the
  ONNX backend. Can swap to ONNX backend (optimum[onnxruntime]) in Phase 4
  polish if startup latency becomes a concern. Model cached in
  ~/.cache/huggingface/ after first use.

- [Phase 1] Chose Chroma embedded mode over sqlite-vec. Reason: chromadb
  has a higher-level API (get_or_create_collection, upsert with metadatas),
  handles cosine similarity natively, and no schema migration needed.
  Data persists to ./chroma_db/ (or CHROMA_PATH env var). No Docker service
  needed — runs entirely in-process.

- [Phase 1] BM25 uses rank-bm25 (in-memory). Index is built lazily from
  Chroma get_all_chunks() on first query after invalidation. This means
  BM25 index and Chroma are always in sync — BM25 reads from Chroma's
  stored documents, not a separate store.

- [Phase 1] Hybrid retrieval uses Reciprocal Rank Fusion (fusion.py already
  existed with correct RRF logic — kept unchanged, no rewrite needed).

- [Phase 1] POST /ingest is a single-phase operation (chunk → embed → store
  in one request). The old code had a two-phase design (store without embed,
  then /analyze to embed). We simplified to one phase because:
  (a) BGE-small local embedding is fast (~16ms/chunk on CPU),
  (b) no rate limits unlike Bedrock Titan,
  (c) API.md contract doesn't specify a two-phase design.

- [Phase 1] Suppressed HF_HUB_DISABLE_SYMLINKS_WARNING in CI. On Windows,
  huggingface_hub warns about symlinks in the model cache. This is a cosmetic
  warning (caching still works), suppressed with env var in CI to keep output
  clean. On Ubuntu CI runners this warning won't appear anyway.

## Known Issues / Open Risks

- The root-level legacy test files (`backend/test_citation_verifier.py`,
  `backend/test_api.py`, `backend/test_adversarial_refusal.py`,
  `backend/test_ingestion.py`, `backend/test_retrieval.py`) are still
  present but NOT collected by pytest. They import old deps (boto3,
  qdrant_client) and have wrong API assumptions. Clean them up in Phase 4.
  Do NOT try to run them directly.

- `backend/conftest.py`, `backend/handler.py`, `backend/samconfig.toml`,
  `backend/template.yaml` are Lambda SAM artifacts. Harmless but stale.
  Delete in Phase 4.

- chroma_db/ directory is created at the repo root when running locally.
  It's gitignored via backend/.gitignore `chroma_db/`. Make sure the root
  .gitignore also ignores it (or place it inside backend/ via CHROMA_PATH).

- BGE-small-en-v1.5 first load takes ~30s on CI (model download ~45MB).
  Subsequent runs use the cache. In CI, model will be re-downloaded on every
  run unless we add a pip cache or HF_HOME cache step. Consider adding
  GitHub Actions cache for ~/.cache/huggingface/ in Phase 4 polish.

- rerank_service.py in app/query/ is an empty stub file. That's fine for
  Phase 1/2. It will be filled in if the NVIDIA rerank stage is attempted
  (Phase 2, optional, hour-22 cut rule applies).

- fusion.py in app/query/ is a pure-Python RRF implementation that already
  existed and is correct. It was kept unchanged.

## What NOT To Redo

- Do NOT re-add postgres or redis to docker-compose.yml.
- Do NOT add boto3 or qdrant_client to requirements.txt.
- Do NOT pin pydantic to 2.7.0.
- Do NOT rewrite fusion.py — it's correct as-is.
- Do NOT change embed_service.py to use Bedrock — the whole point is local.
- Do NOT introduce a two-phase /ingest + /analyze pattern. POST /ingest
  does the full pipeline in one shot (chunk → embed → store).

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): not written yet (Phase 2)
- Ingestion tests: **25/25 passing** (includes 3 RULES.md required tests)
- Retrieval sanity tests: **10/10 passing** (Recall@5 verified, all questions)
- Adversarial refusal set: not written yet (Phase 2)
- Playwright e2e: not written yet (Phase 3)
- CI pipeline: GREEN — 25 tests pass, 0 failures

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

Reading this file, then PHASES.md Phase 2. Phase 2 starts with
`llm_service.py` — configure the OpenAI-compatible client for NVIDIA Build
or OpenRouter (env var `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL`), then
implement `citation_verifier.py` (deterministic fuzzy-match, the core
guardrail), then `planner.py` to wire everything together, and finally
enable POST /query. Write `test_citation_verifier.py` FIRST (DECISION.md
Rule 4 — verifier must have unit tests independent of the full pipeline).