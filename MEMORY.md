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
**Hour mark (approx, since build start):** ~8.5h (Phase 0 + 1)
**Last updated:** 2026-08-07T18:10:00+05:30
**Last updated by:** Antigravity agent, session cfe78a93

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [x] Phase 1 — Ingestion + Retrieval (Bedrock Titan + Qdrant + MongoDB Atlas)
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

- ~~[Phase 1] Chose sentence-transformers (PyTorch backend) over raw ONNX~~ — *Superseded by user directive: User requested AWS Bedrock Titan embeddings (`amazon.titan-embed-text-v2:0`) and lean dependencies for AWS Lambda deployment.*
- ~~[Phase 1] Chose Chroma embedded mode over sqlite-vec~~ — *Superseded by user directive: User requested Qdrant for vector storage.*

- [Phase 1] **AWS Bedrock Titan Text Embeddings v2** (`amazon.titan-embed-text-v2:0`): 1024 dimensions, invoked via `boto3.client("bedrock-runtime")`. Retries with exponential backoff for rate-limiting.
- [Phase 1] **Qdrant Vector DB**: Collections stored with 1024 dimensions, Cosine distance, and payload indexing on `session_id`. Works with Qdrant Cloud (`QDRANT_ENDPOINT` + `QDRANT_API_KEY`) as well as local/in-memory test instances.
- [Phase 1] **MongoDB Atlas**: Document & chunk text store (`chunks` collection), stores all chunk metadata (`chunk_id`, `source_file`, `page_number`, `section_title`, `text`, `session_id`).
- [Phase 1] **In-process BM25**: `rank-bm25` used for keyword retrieval, built dynamically from store chunks with cache invalidation on `/ingest`.
- [Phase 1] **Hybrid Search & Fusion**: Reciprocal Rank Fusion (RRF in `fusion.py`) combines BM25 keyword rankings with Qdrant vector similarity scores.
- [Phase 1] **Lambda Compatibility**: `mangum` and `template.yaml` preserved for AWS Serverless deployment. Removed heavy local PyTorch/sentence-transformers packages from `requirements.txt` to keep the deployment package lightweight.

## Known Issues / Open Risks

- The root-level legacy test files (`backend/test_citation_verifier.py`,
  `backend/test_api.py`, `backend/test_adversarial_refusal.py`,
  `backend/test_ingestion.py`, `backend/test_retrieval.py`) are still
  present but NOT collected by pytest. Clean them up in Phase 4.

- rerank_service.py in app/query/ is an empty stub file. That's fine for
  Phase 1/2. It will be filled in if the NVIDIA rerank stage is attempted
  (Phase 2, optional, hour-22 cut rule applies).

- fusion.py in app/query/ is a pure-Python RRF implementation that already
  existed and is correct. It was kept unchanged.

## What NOT To Redo

- Do NOT re-add postgres or redis to docker-compose.yml.
- Do NOT re-add heavy ML libraries like sentence-transformers/torch.
- Do NOT change embed_service.py away from AWS Bedrock Titan.
- Do NOT change vector storage away from Qdrant.
- Do NOT rewrite fusion.py — it's correct as-is.

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): not written yet (Phase 2)
- Ingestion tests: **25/25 passing** (includes 3 RULES.md required tests)
- Retrieval sanity tests: **10/10 passing** (Recall@5 verified on live Bedrock Titan + Qdrant stack)
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
`llm_service.py` (AWS Bedrock Nova Pro / OpenAI compatible), then
implement `citation_verifier.py` (deterministic fuzzy-match, the core
guardrail), then `planner.py` to wire everything together, and finally
enable POST /query. Write `test_citation_verifier.py` FIRST (DECISION.md
Rule 4 — verifier must have unit tests independent of the full pipeline).