"""
main.py — FastAPI application.

Endpoints:
  POST /ingest   — upload PDF(s) to S3 + chunk to MongoDB; returns session_id immediately.
  POST /analyze  — trigger Bedrock embeddings + Qdrant upsert for a given session_id.
  POST /query    — hybrid retrieval + LLM generation with guardrails.
  GET  /health   — liveness check.

S3 Flow:
  1. On startup, check/create the S3 bucket.
  2. /ingest  → upload to S3 in parallel + chunk to MongoDB (fast, no embedding).
  3. /analyze → embed chunks from MongoDB using Bedrock + upsert to Qdrant.
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ingest.chunker import chunk_document
from app.ingest.store import add_chunks_without_embedding, embed_and_upsert_session
from app.query.bm25_retriever import invalidate_index
from app.shared.config import AWS_REGION, S3_BUCKET_NAME, get_s3_client

app = FastAPI(title="Cited-or-Silent API", version="2.0.0")

# Allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: Ensure S3 bucket exists ─────────────────────────────────────────

@app.on_event("startup")
async def ensure_s3_bucket() -> None:
    """On startup, verify the S3 bucket exists. Create it if missing."""
    try:
        s3 = get_s3_client()
        try:
            s3.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"[startup] S3 bucket '{S3_BUCKET_NAME}' exists [OK]")
        except Exception:
            print(f"[startup] S3 bucket '{S3_BUCKET_NAME}' not found - creating...")
            try:
                if AWS_REGION == "us-east-1":
                    s3.create_bucket(Bucket=S3_BUCKET_NAME)
                else:
                    s3.create_bucket(
                        Bucket=S3_BUCKET_NAME,
                        CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
                    )
                print(f"[startup] S3 bucket '{S3_BUCKET_NAME}' created [OK]")
            except Exception as create_exc:
                if "BucketAlreadyOwnedByYou" in str(create_exc):
                    print(f"[startup] S3 bucket '{S3_BUCKET_NAME}' already owned [OK]")
                else:
                    raise create_exc
    except Exception as exc:
        print(f"[startup] WARNING: Could not verify/create S3 bucket: {exc}")

    # Ensure Qdrant collection + session_id payload index exist on startup
    try:
        from app.ingest.store import _init_qdrant_collection
        _init_qdrant_collection()
        print("[startup] Qdrant collection initialized [OK]")
    except Exception as exc:
        print(f"[startup] WARNING: Could not initialize Qdrant collection: {exc}")


# ── /health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Models ────────────────────────────────────────────────────────────────────

class IngestDocumentResult(BaseModel):
    filename: str
    chunks_created: int
    pages: int
    s3_key: str


class IngestResponse(BaseModel):
    status: str = "uploaded"
    session_id: str
    documents: List[IngestDocumentResult]


class AnalyzeRequest(BaseModel):
    session_id: str


class AnalyzeResponse(BaseModel):
    status: str = "analyzed"
    session_id: str
    total_embedded: int


ALLOWED_SUFFIXES = {".pdf"}


# ── /ingest ──────────────────────────────────────────────────────────────────

def _upload_to_s3(file_bytes: bytes, s3_key: str) -> None:
    """Upload raw bytes to S3. Called in a thread pool for parallelism."""
    s3 = get_s3_client()
    s3.upload_fileobj(
        io.BytesIO(file_bytes),
        S3_BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    print(f"[s3] Uploaded: s3://{S3_BUCKET_NAME}/{s3_key} [OK]")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    """
    Phase 1: Upload PDF(s) to S3 in parallel and chunk to MongoDB.
    Does NOT run Bedrock embeddings — call /analyze next.
    Returns session_id immediately.
    """
    active_session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
    results: List[IngestDocumentResult] = []

    # Read all file bytes up-front (async read)
    file_payloads = []
    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted.",
            )
        raw_bytes = await upload.read()
        file_payloads.append((filename, raw_bytes))

    # Process each file: S3 upload (parallel) + chunk (synchronous, fast)
    futures_map = {}
    with ThreadPoolExecutor(max_workers=min(len(file_payloads), 4)) as executor:
        for filename, raw_bytes in file_payloads:
            s3_key = f"{active_session_id}/{filename}"
            future = executor.submit(_upload_to_s3, raw_bytes, s3_key)
            futures_map[future] = (filename, raw_bytes, s3_key)

        # While S3 uploads run in parallel, chunk each file synchronously
        for filename, raw_bytes, s3_key in futures_map.values():
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name

            try:
                chunks = chunk_document(tmp_path)
            except (ValueError, FileNotFoundError) as exc:
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

            # Store chunks to MongoDB WITHOUT embedding (embedding happens in /analyze)
            add_chunks_without_embedding(chunks, session_id=active_session_id)
            invalidate_index()

            pages = max((c["page_number"] for c in chunks), default=0)
            results.append(
                IngestDocumentResult(
                    filename=filename,
                    chunks_created=len(chunks),
                    pages=pages,
                    s3_key=s3_key,
                )
            )

        # Wait for all S3 uploads to complete
        for future in as_completed(futures_map):
            try:
                future.result()
            except Exception as exc:
                print(f"[s3] Upload warning: {exc}")

    return IngestResponse(session_id=active_session_id, documents=results)


# ── /analyze ──────────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest):
    """
    Phase 2: Read un-embedded chunks from MongoDB for a session, run Bedrock
    Titan embeddings (1.4s sleep per chunk), and upsert to Qdrant.
    This is a long-running operation; frontend should show a progress spinner.
    """
    if not body.session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    try:
        total = embed_and_upsert_session(body.session_id)
        return AnalyzeResponse(session_id=body.session_id, total_embedded=total)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Embedding failed for session '{body.session_id}': {exc}",
        )


# ── /query ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


@app.post("/query")
def query(body: QueryRequest):
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
            detail=f"An error occurred while processing the query: {exc}",
        )
