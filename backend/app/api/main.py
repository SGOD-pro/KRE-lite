"""
main.py — FastAPI application.

Endpoints per API.md:
  POST /ingest   — upload PDF(s), chunk, embed, store
  POST /query    — Phase 2 (placeholder stub for now)
  GET  /health   — liveness check
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ingest.chunker import chunk_document
from app.ingest.store import add_chunks
from app.query.bm25_retriever import invalidate_index

import tempfile
import shutil
import os

app = FastAPI(title="Cited-or-Silent API", version="1.0.0")

# Allow the Vite dev server to talk to us during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── /ingest ──────────────────────────────────────────────────────────────────

class IngestDocumentResult(BaseModel):
    filename: str
    chunks_created: int
    pages: int


class IngestResponse(BaseModel):
    status: str = "ingested"
    documents: List[IngestDocumentResult]


ALLOWED_SUFFIXES = {".pdf"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: List[UploadFile] = File(...)):
    """
    Upload one or more PDF files. Each is chunked, embedded, and stored.

    API.md error contract:
      400 — unsupported file type
      422 — file present but unparseable / no text extracted
    """
    results: List[IngestDocumentResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        # 400: unsupported type
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted.",
            )

        # Write to a temp file so PyMuPDF can open it by path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(upload.file, tmp)

        try:
            chunks = chunk_document(tmp_path)
        except ValueError as exc:
            # ValueError from chunker = unparseable / no text — 422
            raise HTTPException(status_code=422, detail=str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            # Unexpected error — surface cleanly
            raise HTTPException(
                status_code=422,
                detail=f"Failed to process '{filename}': {exc}",
            )
        finally:
            os.unlink(tmp_path)

        # Fix source_file to use the original upload name, not the tmp path
        for c in chunks:
            c["source_file"] = filename

        add_chunks(chunks)
        invalidate_index()   # BM25 must be rebuilt after new chunks added

        pages = max((c["page_number"] for c in chunks), default=0)
        results.append(
            IngestDocumentResult(
                filename=filename,
                chunks_created=len(chunks),
                pages=pages,
            )
        )

    return IngestResponse(documents=results)


# ── /query ────────────────────────────────────────────────────────────────────
# Phase 2 stub — returns 503 with a clear message so tests don't misinterpret.

class QueryRequest(BaseModel):
    question: str


@app.post("/query")
async def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    # Phase 2 placeholder
    raise HTTPException(
        status_code=503,
        detail="Generation pipeline not yet implemented (Phase 2).",
    )
