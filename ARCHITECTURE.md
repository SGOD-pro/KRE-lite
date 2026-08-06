# ARCHITECTURE.md — Single-Service, Hackathon-Scoped

## Deployment Model

ONE FastAPI service. ONE process. No microservices, no Lambda
packaging, no dual dev/prod provider matrix. This is a deliberate
scope decision — see BOUNDARIES.md for what was cut and why.

```text
+-----------------------------------------------------+
|                  FastAPI app (single process)         |
|                                                       |
|  POST /ingest   -> chunker -> embed (BGE-small ONNX)  |
|                     -> store (Chroma/sqlite-vec)      |
|                                                       |
|  POST /query    -> bm25_retriever                     |
|                  -> vector_retriever                  |
|                  -> [optional] nvidia_rerank           |
|                  -> llm_call (structured JSON out)     |
|                  -> citation_verifier  <-- guardrail   |
|                  -> response (answer | refusal)        |
+-----------------------------------------------------+
```

## Module Map

```text
app/
├── ingest/
│   ├── chunker.py          # splits by page + heading, keeps
│   │                       #   page_number + section_title on
│   │                       #   every chunk, no exceptions
│   ├── embed_service.py    # BGE-small-en-v1.5 ONNX, local, CPU
│   └── store.py            # Chroma or sqlite-vec wrapper
├── query/
│   ├── bm25_retriever.py
│   ├── vector_retriever.py
│   ├── rerank_service.py   # NVIDIA Build call — OPTIONAL, feature-
│   │                       #   flagged, safe to disable under
│   │                       #   time pressure
│   ├── llm_service.py      # single call, structured output only
│   ├── citation_verifier.py # THE core guardrail — deterministic
│   │                       #   fuzzy-match of every cited quote
│   │                       #   against its claimed source chunk
│   └── planner.py          # thin: retrieve -> maybe rerank ->
│                           #   generate -> verify -> respond
├── api/
│   └── main.py             # POST /ingest, POST /query, GET /health
└── shared/
    └── schemas.py          # Pydantic models for structured I/O
```

## The Citation Verifier — Design Detail

This is the one component that must be bulletproof. Everything else
in this system is standard RAG plumbing; this is the differentiator.

```text
Input:  LLM's structured output
        {answer_draft, citations: [{page, section, quote}]}
        + the actual retrieved chunks (source of truth)

For each citation:
  1. Look up the chunk claimed by (page, section).
  2. Fuzzy-match `quote` against that chunk's raw text
     (normalized whitespace, case-insensitive, >=90% token overlap
     via simple ratio — NOT exact string match, LLMs paraphrase
     slightly even when asked not to).
  3. PASS -> citation kept, attached to final answer with a
     source-chunk offset for UI highlighting.
  4. FAIL -> citation (and the answer sentence it supports, if we
     can isolate it) is dropped.

Output: if >=1 citation survives -> return answer with surviving
        citations only.
        if 0 citations survive -> return refusal.
```

This is deterministic code, not a second LLM call. Keep it that way
— an LLM "judge" checking an LLM's citations doubles your
hallucination surface and doubles your latency for no guaranteed
gain in a 48-hour build.

## Data Flow — Query Path (happy path)

1. User question -> BM25 top-k candidates
2. BM25 candidates -> BGE-small ONNX embed (local, no API call) ->
   vector similarity re-rank against candidate set
3. (Optional) top vector results -> NVIDIA Build rerank call for a
   final precision pass
4. Top N chunks -> LLM prompt, structured output forced
   (`response_format: json_schema` or function-calling)
5. LLM output -> citation_verifier
6. Verified answer OR refusal -> API response -> UI

## Hard Constraints

- Maximum ONE LLM call per query. No agent loops, no re-planning,
  no self-critique LLM calls. Simplicity is what makes this buildable
  and testable in 48 hours.
- The LLM NEVER sees a raw prompt asking it to "be honest" as the
  only safeguard. The verifier is what actually enforces honesty.
  Prompting for honesty is a nice-to-have layer on top, not the
  guardrail itself.
- Every chunk in storage has `page_number` and `section_title`
  populated. If a document format can't reliably provide these
  (e.g. a PDF with no clear headings), fall back to
  `section_title = "Untitled section, page N"` — never null.
- No local model weights except BGE-small-en-v1.5 ONNX. Everything
  else (rerank, LLM) is an external API call — keeps the Docker
  image small and the setup reproducible for judges.

## Frontend Architecture (see UI-UX.md for detail)

Two-pane layout:
- Left: chat interface (question in, answer + citation chips out)
- Right: source document viewer, auto-scrolls to and highlights the
  cited page/section when a citation chip is clicked

No auth, no multi-tenant, no user accounts. Single-session, local
demo tool. This is explicit in BOUNDARIES.md.
