# API.md — Endpoint Contracts

Two endpoints. That's it. Resist adding more.

## POST /ingest

Uploads one or more documents, chunks them, embeds them, stores them.

**Request:** `multipart/form-data`, one or more files (PDF for the
demo; keep the chunker format-agnostic in principle but only build
and test the PDF path in 48 hours — see BOUNDARIES.md).

**Response:**
```json
{
  "status": "ingested",
  "documents": [
    {
      "filename": "policy_handbook.pdf",
      "chunks_created": 47,
      "pages": 22
    }
  ]
}
```

**Errors:**
- `400` — unsupported file type
- `422` — file present but unparseable (corrupt PDF, scanned image
  with no extractable text — do not silently ingest zero chunks and
  claim success)

## POST /query

**Request:**
```json
{
  "question": "What is the notice period for resignation?"
}
```

**Response — answered case:**
```json
{
  "status": "answered",
  "answer": "The notice period for resignation is 30 days.",
  "citations": [
    {
      "page": 12,
      "section": "Section 4.2 — Termination and Resignation",
      "quote": "employees must provide a minimum of 30 days written notice",
      "chunk_id": "doc1_chunk_0038"
    }
  ]
}
```

**Response — refusal case:**
```json
{
  "status": "refused",
  "reason": "no_grounded_answer",
  "message": "I don't have enough information in the provided documents to answer that."
}
```

Note: `status` is always one of exactly two values. The frontend
branches on this field, not on whether `citations` is empty — the
API contract makes refusal a first-class response shape, not an
edge case the client has to infer (DECISION.md Rule 5, AGENT.md).

**Errors:**
- `400` — empty question
- `503` — LLM or rerank provider unavailable (return this cleanly,
  do not fall back to an unverified answer just because the provider
  call failed — DECISION.md Rule 6 applies even under infra failure)

## v1.1 Additions (post-deploy only)

### POST /query — response addendum (v1.1)

Add fields to existing "answered" response shape:
```json
{
  "status": "answered",
  "answer": "...",
  "citations": [...],
  "confidence_tier": "high",
  "confidence_score": 0.91,
  "metrics": {
    "latency_ms": 1180,
    "prompt_tokens": 450,
    "completion_tokens": 85,
    "total_tokens": 535,
    "pages_searched": 3,
    "pages_total": 45
  }
}
```
`confidence_tier` one of `"high" | "low"`. Refuse case unchanged
shape from v1, but add `"pages_searched": 0` (query never left tier
1 filter).

### POST /audit

**Request:**
```json
{
  "ruleset": [
    "Must have a fire extinguisher within 10 feet.",
    "Must list a backup communication protocol."
  ]
}
```
(assumes doc already ingested via /ingest)

**Response:**
```json
{
  "status": "complete",
  "results": [
    {
      "rule": "Must have a fire extinguisher within 10 feet.",
      "verdict": "pass",
      "citations": [{"page": 8, "section": "Safety Equipment", "quote": "..."}]
    },
    {
      "rule": "Must list a backup communication protocol.",
      "verdict": "unable_to_verify",
      "citations": []
    }
  ],
  "metrics": {"total_tokens": 1820, "latency_ms": 4300}
}
```
`verdict` one of `"pass" | "fail" | "unable_to_verify"` —
DECISION.md Rule 14, never force pass/fail w/o evidence.

## GET /health

Trivial liveness check for docker-compose / CI. Returns `{"status":
"ok"}`. Used in Phase 0 exit criteria.

## Internal Contract: LLM Structured Output Schema

This is what `llm_service.py` forces the model to return — not
user-facing, but documented here because the citation_verifier
depends on this shape exactly:

```json
{
  "type": "object",
  "properties": {
    "answer_draft": {"type": "string"},
    "citations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "page": {"type": "integer"},
          "section": {"type": "string"},
          "quote": {"type": "string"}
        },
        "required": ["page", "section", "quote"]
      }
    }
  },
  "required": ["answer_draft", "citations"]
}
```

If the LLM returns anything that doesn't validate against this
schema, treat it as zero citations survived (DECISION.md Rule 3) —
do not attempt to salvage a malformed response by regex-parsing free
text out of it.