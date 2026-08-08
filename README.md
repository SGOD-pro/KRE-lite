# KRE-lite 🤫

An enterprise-grade, citation-anchored Document Question-Answering system. Every answer the system returns is traced to a verbatim quote on a specific page and section of an ingested document. If no grounded quote can be found, the system refuses to answer — never hallucinates.

**Core stack:** FastAPI backend · AWS Bedrock Titan Embeddings v2 (1024-dim) · Qdrant Cloud (vector store) · MongoDB Atlas (chunk text store) · In-process BM25 · Reciprocal Rank Fusion · AWS Bedrock Nova Pro (LLM, 1 call per query) · Deterministic citation verifier · Vite/React frontend.

---

## 🏛️ System Architecture

```
[ PDF Document ] ────────► [ PyMuPDF Chunker (Page + Heading) ]
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
[ Bedrock Titan Embeddings v2 ]                          [ In-Process BM25 ]
            │                                                   │
            ▼                                                   │
[ Qdrant Vector Cloud ]                                         │
            │                                                   │
            └─────────────────────────┬─────────────────────────┘
                                      ▼
                      [ Reciprocal Rank Fusion (RRF) ]
                                      │
                                      ▼
                        [ AWS Bedrock Nova Pro (LLM) ]
                         (single structured-JSON call)
                                      │
                                      ▼
                    [ Deterministic Citation Verifier ]
                      (Python fuzzy-match, no LLM call)
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
             [ Verified Answer ]               [ Clean Refusal ]
             (with page/quote chips)           (Amber Guardrail Card)
```

Chunk metadata is dual-written: vector payloads to Qdrant, full text to MongoDB Atlas. BM25 index is built from MongoDB at query time, invalidated on every `/ingest`.

---

## 📊 Measured System Performance

Numbers below come from the test suite (`pytest tests/unit/`) and `benchmark_evaluation.py` run against the live stack. No comparison to external baselines is made — the numbers speak for themselves.

### Adversarial Guardrail Test Set (19 questions across 4 categories)

| Category | Questions | Status Breakdown | Pass Rate |
| :--- | :---: | :---: | :---: |
| Adjacent-but-absent facts | 5 | 5 Refused / 0 Answered | 5/5 (100%) |
| Wrong entity / number swap | 5 | 5 Corrected with Grounding / 0 Answered | 5/5 (100%) |
| Out-of-corpus | 5 | 5 Refused / 0 Answered | 5/5 (100%) |
| Leading questions with false premises | 4 | 2 Refused / 2 Corrected / 0 Answered | 4/4 (100%) |
| **Total** | **19** | **12 Refused / 7 Corrected / 0 Answered** | **19/19 (100%)** |

> **3-State Response Machine (DECISION.md Rule 15):** When a user asks a false-premise question and the document contains verified contradictory facts, the system transitions to `status: "corrected"`, explicitly highlighting the contradiction with verbatim citations rather than silently answering around it. If no grounding exists, the system deterministically emits `status: "refused"`.

### Citation Faithfulness & Token Economics (`benchmark_evaluation.py`)

| Metric | Measured Value | Note |
| :--- | :---: | :--- |
| **Citation Faithfulness** | **100.0%** | All returned quotes verified against source chunk text |
| **Average End-to-End Latency** | **3,707 ms** | Live Bedrock Titan + Nova Pro + Qdrant stack |
| **P95 Latency** | **10,878 ms** | Includes cold-start vector search initialization |
| **Average Prompt Tokens** | **1,320.9 tokens** | Structured context + system prompt formatting |
| **Average Completion Tokens** | **181.1 tokens** | Precise answer + JSON citations schema |
| **Estimated Cost per 1k Queries** | **~$1.64 / 1,000 queries** | Based on AWS Bedrock Nova Pro ($0.80/M in, $3.20/M out) + Titan v2 ($0.02/M) |
| **LLM Calls per Query** | **1** | Single-call architecture (DECISION.md Rule 1) |
| **Citation Verifier Overhead** | **< 5 ms** | Deterministic Python fuzzy matching, zero LLM cost |

### Prompt Injection & Security Guardrails (`test_security_guardrail.py`)

- **12 attack vectors tested** (system prompt overrides, jailbreaks, role impersonation, delimiter breakouts, secret exfiltration)
- **12/12 correctly blocked** by pre-LLM regex filter at 0 token cost
- **5 benign queries** pass without false positives
- **25/25 total test cases pass** in `test_security_guardrail.py`

---

## 🛡️ Multi-Layer Prompt Injection & Security Guardrails

Three implemented and tested defenses:

1. **Pre-Execution Regex Filter (`app/query/security_guardrail.py`)** — deterministic pattern matching detects instruction overrides, jailbreak keywords, delimiter breakout tokens (`<|im_start|>`, `[INST]`), and secret exfiltration attempts. Triggers refusal at 0 token cost before the query reaches the LLM. **Tested: `test_security_guardrail.py`, 25 test cases, all passing.**

2. **Structural XML Sandboxing (`app/query/llm_service.py`)** — retrieved chunks and user questions are wrapped in `<context_documents>` / `<user_question>` tags with an explicit system instruction prohibiting execution of meta-commands found in those sections.

3. **Deterministic Citation Verification (`app/query/citation_verifier.py`)** — even if an injected payload causes the LLM to generate an answer, any response without a verified verbatim quote matching a real ingested chunk is refused. This is the backstop that cannot be bypassed through prompting.

---

## 🐳 One-Command Docker Setup (Recommended)

### 1. Configure Environment

Copy the example environment file and fill in your AWS, Qdrant, and MongoDB credentials:

```bash
cp .env.example .env
```

Required variables in `.env`:
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-south-1
QDRANT_ENDPOINT=https://...cloud.qdrant.io:6333
QDRANT_API_KEY=...
MONGODB_URI=mongodb+srv://...
MONGODB_DB=cited_or_silent
```

### 2. Run with Docker Compose

```bash
docker compose --env-file .env up --build -d
```

- **Frontend Web UI**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`

---

## 🚀 Local Development Setup

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`.

---

## 🧪 Testing & Benchmarks

### 1. Pytest Unit & Adversarial Test Suite

```bash
cd backend
pytest tests/unit/ -v
```

Test modules:
- `test_citation_verifier.py` — verifier unit tests (exact/fuzzy match, failure modes)
- `test_adversarial_refusal.py` — 19 adversarial questions, parametrized
- `test_ingestion.py` — chunker + ingest endpoint contract tests
- `test_retrieval.py` — Recall@5 sanity checks on known questions
- `test_query_pipeline.py` — positive grounded query tests
- `test_health.py` — health + session validation endpoint tests
- `test_security_guardrail.py` — 25 prompt injection detection tests

### 2. System Benchmark (Faithfulness & Guardrails)

```bash
cd backend
python benchmark_evaluation.py
```

Writes results to `benchmark_results.json`.

### 3. Playwright End-to-End Test Suite

Requires the backend to be running (`uvicorn` or `docker compose up`) and AWS credentials active (the E2E suite ingests real PDFs via Bedrock Titan).

```bash
cd frontend
npx playwright test
```

---

## 🔑 GitHub Secrets for CI/CD

CI (`ci.yml`) runs on every push. CD (`cd.yml`) is manually triggered via `workflow_dispatch`.

### CI Secrets (required for `pytest tests/unit/` to pass against live stack)

| Secret Name | Description |
| :--- | :--- |
| `AWS_ACCESS_KEY_ID` | IAM key with Bedrock, S3 permissions |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | e.g. `ap-south-1` |
| `QDRANT_ENDPOINT` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB` | MongoDB database name |

### CD Secrets (required for deployment via `cd.yml`)

| Secret Name | Description |
| :--- | :--- |
| `AWS_ACCESS_KEY_ID` | (same as above) |
| `AWS_SECRET_ACCESS_KEY` | (same as above) |
| `QDRANT_ENDPOINT` | (same as above) |
| `QDRANT_API_KEY` | (same as above) |
| `MONGODB_URI` | (same as above) |
| `VERCEL_TOKEN` | Vercel Personal Access Token |
| `VERCEL_ORG_ID` | Vercel Team/User ID |
| `VERCEL_PROJECT_ID` | Vercel Project ID |

---

## 📋 Non-Negotiables Compliance Checklist

- [x] **Zero fabrication guarantee**: Deterministic citation verifier strips any ungrounded claim before it reaches the user.
- [x] **Adversarial guardrails**: 19/19 adversarial questions correctly refused or corrected (3-state machine: refused / corrected / answered — Phase C+D verified 100% stable across 3 independent runs).
- [x] **Single LLM call**: One structured-JSON call per query (DECISION.md Rule 1).
- [x] **Two-Pane UI**: Split-view with interactive citation highlight and source scroll (UI-UX.md).
- [x] **Dockerized**: `docker compose up` brings up backend + frontend.
- [x] **CI/CD Ready**: GitHub Actions `ci.yml` runs pytest + frontend build on every push.
