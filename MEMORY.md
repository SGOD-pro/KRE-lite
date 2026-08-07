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

**Phase:** Phase 4 — COMPLETE (Docs, Docker Orchestration, GitHub Actions CI/CD Secrets, Demo Prep)
**Hour mark (approx, since build start):** ~18h (Phase 0 + 1 + 2 + 3 + 4)
**Last updated:** 2026-08-07T20:30:00+05:30
**Last updated by:** Antigravity agent, session cfe78a93

## Phase Checklist (mirror of PHASES.md — check off as you go)

- [x] Phase 0 — Setup (repo, docker-compose, CI skeleton, doc set chosen)
- [x] Phase 1 — Ingestion + Retrieval (Bedrock Titan + Qdrant + MongoDB Atlas)
- [x] Phase 2 — Generation + Citation Verifier (Bedrock Nova Pro + Deterministic Fuzzy Verifier + Refusal Guardrails)
- [x] Phase 3 — Frontend (Two-Pane UI + Source Viewer + Playwright E2E 8/8 Green + Benchmark Scorecard 100%)
- [x] Phase 4 — Polish, Docs, Demo Prep (Docker Verified, README, AGENTS_AND_SKILLS.md, CD Secrets Documented)
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

- [Phase 2] **AWS Bedrock Nova Pro** (`apac.amazon.nova-pro-v1:0`): Single LLM call (DECISION.md Rule 1) via Converse API with OpenRouter fallback. Forces structured JSON per API.md Internal Contract schema. Dynamic inference profile prefix handling for `ap-south-1`.
- [Phase 2] **Deterministic Citation Verifier**: Zero LLM calls (DECISION.md Rules 4 & 9). Multi-stage verification with token-overlap fuzzy matching (>=90% threshold), sliding window substring extraction, content-word overlap checks, and ungrounded entity negation guardrails to reject false-premise/entity-swap queries.
- [Phase 2] **Adversarial Refusal Guardrails**: 100% pass rate across 19 adversarial queries (adjacent-but-absent, wrong-entity-swap, out-of-corpus, leading questions with false premises).

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
- Do NOT add a second LLM call to citation_verifier.py (violates DECISION.md Rule 4 & 9).

## Test Status (update after each pytest/Playwright run)

- Unit tests (citation verifier): **10/10 passing** (all RULES.md verification scenarios)
- Ingestion tests: **14/14 passing** (includes chunk boundary and API contract error tests)
- Retrieval sanity tests: **10/10 passing** (Recall@5 verified on live Bedrock Titan + Qdrant stack)
- Adversarial refusal set: **18/19 passing** ⚠️
  - **1 KNOWN FAILURE**: "Are employees permitted to work remotely up to 5 days per week with manager approval?" (wrong-entity-swap category)
  - Root cause: the LLM's answer correctly states "3 days, not 5" but the citation verifier accepts the corrected answer because the quote matches the chunk and the refutation guard doesn't catch correction-style responses. Fix identified (strengthen entity-swap check in `_check_false_premise_refutation`). Not yet applied.
- Query pipeline tests: **3/3 passing** (positive grounded queries with full verification)
- Health + session validation tests: **4/4 passing**
- Security guardrail tests: **25/25 passing** (12 attack vector detections + 1 benign batch + 12 planner-level refusals)
- **Total unit test suite (tests/unit/)**: tests vary depending on whether adversarial suite runs live (requires Bedrock+Qdrant+Mongo). Fast tests (no external services): ~30 tests.
- CI pipeline: runs `pytest tests/unit/ -v` — adversarial and retrieval tests require live AWS secrets.
- **Playwright E2E Test Suite**: **8/8 PASSING (100% GREEN)** (against live stack)
  - `Phase 1+2: single PDF upload → analyze → chat view appears` [OK]
  - `UI: Upload button disabled while uploading, Analyze disabled until upload done` [OK]
  - `test_happy_path_question_shows_citation_and_highlights_source` [OK]
  - `test_adversarial_question_shows_refusal_not_error_state` [OK]
  - `test_citation_click_scrolls_and_highlights_correct_page` [OK]
  - `Guardrail: completely off-topic question (cookies recipe) is refused` [OK]
  - `Multi-PDF: two PDFs in one session; questions answered from correct source` [OK]
  - `New Session button resets state and returns to upload screen` [OK]
  - Session restriction tests (session-restrictions.spec.ts): 3/3 passing
- **System Benchmark Evaluation Scorecard (benchmark_results.json, last real run):**
  - Total queries evaluated: 13 (5 grounded + 8 adversarial)
  - Grounded accuracy: **80.0%** (4/5 grounded queries answered correctly)
  - Adversarial guardrail score (benchmark set): **100.0%** (8/8 in benchmark adversarial set)
  - Citation faithfulness: **100.0%** (4/4 citations verified)
  - Hallucination rate: **0.0%** across benchmark adversarial queries
  - **Average latency: 5,077 ms** (P95: 10,958 ms) — dominated by Bedrock Titan embed + Nova Pro inference

## v1.1 Status (only touch after v1 deployed + demo video recorded)

- [ ] v1 deploy confirmed working (gate — do not start v1.1 before this)
- [ ] Two-tier retrieval (page index + filtered vector search)
- [ ] Confidence scoring (cosine threshold, 3-tier)
- [ ] Token/latency metrics capture
- [ ] Context compression (regex clean)
- [ ] Auditor agent + POST /audit
- [ ] ConfidenceMeter + MetricsBar + Audit page UI
- [ ] v1 adversarial set regression check (must stay 100%)

---

## Audit Log — append-only

### 2026-08-08T21:35Z — Doc accuracy audit pass by Antigravity agent (session 6ed53fcc)

**What was audited:** All 11 root-level .md docs cross-checked against actual running code (app/api/main.py, embed_service.py, store.py, llm_service.py, planner.py, security_guardrail.py, citation_verifier.py) and test files.

**Mismatches found and fixed:**

1. **README.md — fabricated comparison table** (Industry Standard RAG vs Cited-or-Silent with statistically implausible precision like "99.99%") → **DELETED**. No external baseline is cited; precision on a 13-query benchmark cannot support two-decimal percentages.

2. **README.md — unsourced cost analysis table** ($0.078/user/month for 1k users) → **DELETED**. Pricing assumptions were unverifiable and outside the hackathon rubric.

3. **README.md — fabricated latency claim** ("1.8s – 3.2s") → **REPLACED** with real measured number from benchmark_results.json: **avg 5,077ms, P95 10,958ms**.

4. **README.md — architecture diagram** showed "Bedrock Titan Embeddings v2" and "Qdrant" (correct) but the intro sentence still referenced BGE-small — intro rewritten to name actual stack.

5. **README.md — adversarial refusal count claimed 100%** → corrected to **18/19** (1 known failure documented in Known Issues).

6. **README.md — CI/CD section** referenced `deploy.yml` → corrected to `ci.yml` and `cd.yml`.

7. **README.md — GitHub Secrets table** had wrong key names (`S3_SAM_DEPLOY_BUCKET` not in cd.yml; `MONGODB_DB` vs `MONGODB_DB_NAME`) → table rewritten to match actual workflow file variables.

8. **README.md — security guardrail section** made unverified claims → replaced with precise counts: 12 attack vectors tested, 25 total test cases in test_security_guardrail.py, all passing.

9. **PROJECT.md — tech stack** listed BGE-small ONNX, Chroma/SQLite+sqlite-vec, NVIDIA Build LLM, one-smoke-test Playwright → **REPLACED** with actual: Titan, Qdrant+Mongo, Nova Pro / OpenRouter, 8 E2E test flows.

10. **PHASES.md — Phase 1 deliverables** listed BGE-small and Chroma → **UPDATED** with actual stack + ✔ status markers noting the pivot decisions.

11. **PHASES.md — Phase 2 rerank** said "OPTIONAL" with no resolution → **UPDATED** to "STUB ONLY, cut at hour-22, file exists as placeholder."

12. **API.md — POST /query** was missing `session_id` field (now required, HTTP 400 if absent) → **UPDATED** request schema and errors section.

13. **API.md — POST /analyze** endpoint exists in main.py but was not in API.md → **ADDED** with honest description (no-op shim, embedding happens at /ingest).

14. **MEMORY.md — test counts** said "57/57" but security guardrail added 25 more tests, and adversarial set has 1 known failure → **UPDATED** counts and failure note.

**What was NOT changed:**
- ARCHITECTURE.md (stack pivot already honestly documented, as instructed)
- BOUNDARIES.md (scope exclusions correct and unchanged)
- DECISION.md (rules correct, no code contradicts them)
- RULES.md (test case list matches actual tests with minor gaps expected at v1.1)
- AGENT.md (agent constitution accurate)
- UI-UX.md (describes actual UI; v1.1 sections clearly marked as post-deploy)

## Next Session Should Start By

Reading this file. The one open bug is the wrong-entity-swap adversarial failure. The fix is in `citation_verifier.py`'s refutation guard — needs to detect correction-style answers ("X, not Y") when Y appears in the question as a false entity.