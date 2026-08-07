"""
app/api/main.py — FastAPI application entry-point.

Endpoints per API.md:
  GET  /health   → {"status": "ok"}
  POST /ingest   → chunk + embed + store PDFs; returns chunk counts per doc
  POST /query    → retrieve → generate → verify → respond (answered or refused)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.shared.schemas import IngestDocumentResult, IngestResponse, QueryRequest
from app.query.planner import answer_question

app = FastAPI(title="Cited-or-Silent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_SUFFIXES = {".pdf"}


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    """Liveness probe. Phase 0 exit criterion — must never regress."""
    return {"status": "ok"}


# ── POST /ingest ──────────────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    """
    Upload one or more PDFs, chunk them, embed, and store.

    API.md errors:
      400 — unsupported file type
      422 — file present but unparseable (corrupt PDF or no extractable text)

    Response shape per API.md:
      {"status": "ingested", "documents": [{"filename", "chunks_created", "pages"}]}
    """
    from app.ingest.chunker import chunk_document
    from app.ingest.store import add_chunks
    from app.query.bm25_retriever import invalidate_index
    import time

    # Always ensure we have a real session_id so chunks and response are consistent
    if not session_id:
        session_id = f"session_{int(time.time() * 1000)}"

    results: List[IngestDocumentResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        # API.md: 400 for unsupported file type
        if suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted.",
            )

        raw_bytes = await upload.read()

        # Write to a temp file for PyMuPDF (needs a file path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        try:
            # API.md: 422 if file is present but unparseable
            try:
                chunks = chunk_document(tmp_path)
            except (ValueError, FileNotFoundError) as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            except Exception as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to process '{filename}': {exc}",
                )

            # Tag chunks with original filename
            for c in chunks:
                c["source_file"] = filename

            # Embed + store
            add_chunks(chunks, session_id=session_id)
            # Invalidate BM25 index so next query rebuilds from updated store
            invalidate_index()

            pages = max((c["page_number"] for c in chunks), default=0)
            results.append(
                IngestDocumentResult(
                    filename=filename,
                    chunks_created=len(chunks),
                    pages=pages,
                )
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return IngestResponse(documents=results, session_id=session_id)


# ── POST /analyze ─────────────────────────────────────────────────────────────

class AnalyzePayload(BaseModel):
    session_id: Optional[str] = None


@app.post("/analyze")
def analyze(payload: Optional[AnalyzePayload] = None) -> dict[str, str]:
    """Compatibility endpoint for session analysis."""
    return {"status": "analyzed"}


# ── POST /query ───────────────────────────────────────────────────────────────

class QueryPayload(BaseModel):
    question: str
    session_id: Optional[str] = None


@app.post("/query")
def query(payload: QueryPayload) -> dict[str, Any]:
    """
    POST /query endpoint per API.md.

    Returns:
      Answered case:
        {
          "status": "answered",
          "answer": str,
          "citations": [
            {"page": int, "section": str, "quote": str, "chunk_id": str}
          ]
        }
      Refused case:
        {
          "status": "refused",
          "reason": "no_grounded_answer",
          "message": "I don't have enough information in the provided documents to answer that."
        }

    Errors:
      400 — empty question
      503 — provider error
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    try:
        result = answer_question(payload.question, session_id=payload.session_id)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Query service unavailable: {exc}",
        )
