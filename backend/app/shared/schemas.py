"""
shared/schemas.py — Pydantic models for structured I/O per API.md.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


# ── Ingestion schemas ─────────────────────────────────────────────────────────

class IngestDocumentResult(BaseModel):
    filename: str
    chunks_created: int
    pages: int


class IngestResponse(BaseModel):
    status: str = "ingested"
    session_id: Optional[str] = None
    documents: List[IngestDocumentResult]


# ── Query schemas ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class Citation(BaseModel):
    page: int
    section: str
    quote: str
    chunk_id: str


class AnsweredResponse(BaseModel):
    status: str = "answered"
    answer: str
    citations: List[Citation]


class RefusedResponse(BaseModel):
    status: str = "refused"
    reason: str = "no_grounded_answer"
    message: str = (
        "I don't have enough information in the provided documents to answer that."
    )


# ── Internal LLM output schema (used by citation_verifier) ───────────────────

class LLMCitationRaw(BaseModel):
    page: int
    section: str
    quote: str


class LLMStructuredOutput(BaseModel):
    answer_draft: str
    citations: List[LLMCitationRaw]
