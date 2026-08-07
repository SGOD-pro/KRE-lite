# PROJECT.md — Cited-or-Silent: A Zero-Fabrication Document QA Agent

## What We Are Building

A document Q&A agent that answers questions ONLY from provided source
documents, where every claim is anchored to an exact page and
section/heading — and where the agent explicitly refuses to answer
rather than guess when the source doesn't support a confident answer.

This is Track C: Knowledge and Compliance Agents.

## The One-Sentence Pitch

"Every answer either points to a specific page and section, or it
says 'I don't know' — and we can prove both halves of that claim
with an automated test suite, live, in front of you."

## Why This, Not a Bigger RAG System

We are explicitly NOT building a general-purpose enterprise RAG
platform. We are building the smallest system that can make one
narrow claim extremely well: **this agent does not fabricate.**
Everything in this doc set exists to protect that one claim within a
48-hour build window.

## Core Guardrail (this is the whole product)

1. Every chunk stored at ingestion time carries a mandatory
   `page_number` and `section_title` (or `heading_path`) field.
   No chunk without this metadata is ever stored.
2. The LLM is never allowed to answer in free text. It must return
   structured output: `{answer, citations: [{page, section, quote}]}`.
3. A **verifier step** (deterministic code, not a second LLM call)
   checks that every `quote` in every citation is an actual
   substring (fuzzy-matched, see RULES.md) of the retrieved chunk it
   claims to come from. If a citation fails verification, that claim
   is stripped from the answer before it reaches the user.
4. If, after verification, the answer has zero surviving citations,
   the API returns a refusal (`"I don't have enough information in
   the provided documents to answer that."`) — never a bare-LLM
   fallback answer.
5. This refusal path is not a fallback error case — it is a
   first-class, tested product behavior. See RULES.md for the
   adversarial test set that proves it.

## Tech Stack (as built)

```text
Backend:    FastAPI (single service, single process, uvicorn)
Embedding:  AWS Bedrock Titan Text Embeddings v2
            (amazon.titan-embed-text-v2:0, 1024-dim, via boto3)
Rerank:     Not implemented — cut per PHASES.md hour-22 rule.
            rerank_service.py exists as a stub only.
LLM:        AWS Bedrock Nova Pro (apac.amazon.nova-pro-v1:0),
            single structured-JSON call via Converse API.
            OpenRouter (meta-llama/llama-3.1-70b-instruct) as fallback.
Retrieval:  BM25 (rank-bm25, in-process) + Qdrant vector search
            -> Reciprocal Rank Fusion -> LLM -> citation verifier
Storage:    Qdrant Cloud (vector + payload) + MongoDB Atlas
            (full chunk text). Dual-write on ingest.
Frontend:   Vite + React + TypeScript — 2-pane layout
            (chat + source viewer with highlighted citation)
Testing:    pytest (unit + adversarial refusal set), Playwright
            (8 E2E test flows in tests/e2e/)
Deploy:     docker-compose (backend + frontend). CI via GitHub Actions
            ci.yml. CD via cd.yml (manual trigger, workflow_dispatch).
```

## What Judges See in the Demo (3 minutes)

1. Upload a small set of real PDFs (10-30 pages total).
2. Ask a question the docs answer clearly -> get an answer with a
   visible page+section citation, click it, source highlights.
3. Ask a question the docs do NOT answer -> get an honest refusal,
   not a hallucinated answer.
4. Show the adversarial test suite running green in CI — this is
   the "we can prove it" moment, not just "trust us."

## Non-Negotiables Mapping (from the hackathon deck)

| Non-negotiable | How this project satisfies it |
|---|---|
| Architecture document | This file + ARCHITECTURE.md |
| Agent rules / constitution | AGENT.md |
| Working code | docker-compose up, demonstrable end to end |
| Custom agent + custom skill | Citation-verifier agent (AGENT.md) + a "refusal test generator" skill (see RULES.md) |
| Green CI/CD | GitHub Actions running pytest + Playwright on every push |
