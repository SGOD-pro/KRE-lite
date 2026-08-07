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

import uuid
from typing import List, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

class IngestDocumentResult(BaseModel):
    filename: str
    chunks_created: int
    pages: int


class IngestResponse(BaseModel):
    status: str = "ingested"
    session_id: str
    documents: List[IngestDocumentResult]


ALLOWED_SUFFIXES = {".pdf"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Upload one or more PDF files. Each is chunked, embedded, and stored.
    Returns session_id for persistence.
    """
    results: List[IngestDocumentResult] = []
    active_session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted.",
            )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(upload.file, tmp)

        try:
            chunks = chunk_document(tmp_path)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to process '{filename}': {exc}",
            )
        finally:
            os.unlink(tmp_path)

        for c in chunks:
            c["source_file"] = filename

        add_chunks(chunks, session_id=active_session_id)
        invalidate_index()

        pages = max((c["page_number"] for c in chunks), default=0)
        results.append(
            IngestDocumentResult(
                filename=filename,
                chunks_created=len(chunks),
                pages=pages,
            )
        )

    return IngestResponse(session_id=active_session_id, documents=results)


# ── /query ────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


@app.post("/query")
async def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
        
    from app.query.planner import answer_question
    
    try:
        result = answer_question(body.question, session_id=body.session_id)
        return result
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the query: {exc}"
        )
