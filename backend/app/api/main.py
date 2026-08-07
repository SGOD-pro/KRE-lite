"""
app/api/main.py — FastAPI application entry-point.

Phase 0: hello-world skeleton.
  GET  /health   → {"status": "ok"}                  [implemented]
  POST /ingest   → 501 Not Implemented (Phase 1)     [stub]
  POST /query    → 501 Not Implemented (Phase 2)     [stub]

Phase 1 will import from app.ingest.* and app.query.* here.
Do NOT add Phase 1+ imports to this file until Phase 1 is in progress.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cited-or-Silent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Liveness probe. Must return 200. Phase 0 exit criterion."""
    return {"status": "ok"}


@app.post("/ingest", status_code=501)
def ingest() -> dict:
    """Phase 1 stub — POST /ingest will accept PDF uploads."""
    return {"error": "not_implemented", "phase": "Phase 1"}


@app.post("/query", status_code=501)
def query() -> dict:
    """Phase 2 stub — POST /query will run retrieve→generate→verify."""
    return {"error": "not_implemented", "phase": "Phase 2"}
