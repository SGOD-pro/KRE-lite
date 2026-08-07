# Cited-or-Silent 🤫

An enterprise-grade, zero-hallucination Document Question-Answering system powered by **AWS Bedrock (Titan & Nova Pro)**, **Qdrant**, and **MongoDB Atlas**. It enforces strict factual grounding through an invariant-enforcing deterministic verification agent that actively refuses to answer questions containing false premises or ungrounded claims.

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
                                      │
                                      ▼
                    [ Deterministic Citation Verifier ]
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
             [ Verified Answer ]               [ Clean Refusal ]
             (with page/quote chips)           (Amber Guardrail Card)
```

---

## 🐳 One-Command Docker Setup (Recommended)

### 1. Configure Environment
Copy the example environment file and fill in your AWS, Qdrant, and MongoDB credentials:
```bash
cp .env.example .env
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

### 2. System Benchmark Scorecard (Faithfulness & Guardrails)
```bash
cd backend
python benchmark_evaluation.py
```

### 3. Playwright End-to-End Test Suite
```bash
cd frontend
npx playwright test
```

---

## 🔑 GitHub Secrets for CI/CD Deployment

To enable automated Continuous Deployment (`.github/workflows/deploy.yml`), add the following secrets in **GitHub Repository Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**:

### 1. Backend Deployment Secrets (AWS Lambda via SAM)
| Secret Name | Description | Example Value |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | AWS IAM Access Key ID with Bedrock, Lambda, API Gateway, S3 permissions | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_DEFAULT_REGION` | AWS Region where Bedrock Titan & Nova Pro are active | `ap-south-1` or `us-east-1` |
| `S3_SAM_DEPLOY_BUCKET` | Existing S3 bucket for SAM artifact packaging | `cited-or-silent-sam-artifacts` |
| `S3_BUCKET_NAME` | S3 bucket for document storage | `cited-or-silent-docs` |
| `QDRANT_ENDPOINT` | Qdrant Cloud Cluster URL | `https://xxxxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | Qdrant Cloud API Key | `th1s-1s-y0ur-qdr4nt-k3y` |
| `MONGODB_URI` | MongoDB Atlas Connection String | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DB` | MongoDB Database Name | `hackathon_db` |

### 2. Frontend Deployment Secrets (Vercel)
| Secret Name | Description | Where to find |
| :--- | :--- | :--- |
| `VERCEL_TOKEN` | Vercel Personal Access Token | Vercel Account Settings $\rightarrow$ Tokens |
| `VERCEL_ORG_ID` | Vercel Team / User ID | Vercel Project Settings $\rightarrow$ General |
| `VERCEL_PROJECT_ID` | Vercel Project ID | Vercel Project Settings $\rightarrow$ General |

---

## 📋 Non-Negotiables Compliance Checklist

- [x] **Zero Hallucination Guaranteed**: Deterministic citation verifier strips ungrounded claims.
- [x] **Adversarial Guardrails**: 100% clean refusal on false premises and out-of-corpus queries.
- [x] **Single LLM Call**: Single-call structured JSON generation (DECISION.md Rule 1).
- [x] **Two-Pane UI**: Split-view with interactive citation highlight scrolling (UI-UX.md).
- [x] **Dockerized**: One-command `docker compose up` orchestration.
- [x] **CI/CD Ready**: Green GitHub Actions workflows for testing and deployment.
