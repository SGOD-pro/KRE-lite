"""
test_api.py — FastAPI endpoint tests using TestClient (no real server process).

Tests:
  GET  /health        — always passes, no AWS/DB needed
  POST /ingest        — 400 on wrong file type, 422 on empty PDF
                        (real embed+store path skipped in unit test;
                         store.add_chunks is mocked so no RDS needed)
  POST /query (stub)  — confirms Phase 2 stub returns 503
"""
import sys
from pathlib import Path
import io
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.api.main import app
import fitz  # PyMuPDF

client = TestClient(app)

FIXTURE_PDF = Path(__file__).parent / "tests" / "fixtures" / "sample_doc.pdf"


# ── /health ───────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── /ingest — 400 unsupported type ───────────────────────────────────────────

def test_ingest_unsupported_type_returns_400():
    fake_docx = io.BytesIO(b"fake docx content")
    r = client.post(
        "/ingest",
        files={"files": ("document.docx", fake_docx, "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "Unsupported file type" in r.json()["detail"]


# ── /ingest — 422 empty/scanned PDF ──────────────────────────────────────────

def test_ingest_empty_pdf_returns_422():
    """A PDF with a blank page and no text should return 422."""
    doc = fitz.open()
    doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    r = client.post(
        "/ingest",
        files={"files": ("blank.pdf", buf, "application/pdf")},
    )
    assert r.status_code == 422
    assert "no extractable text" in r.json()["detail"]


# ── /ingest — happy path (mock embed + store) ─────────────────────────────────

def test_ingest_pdf_happy_path_mocked():
    """
    Test the full /ingest route logic with real chunking but mocked
    embed + store so no AWS/RDS connection is required.
    """
    if not FIXTURE_PDF.exists():
        pytest.skip("Fixture PDF not found — run create_fixture_pdf.py first")

    pdf_bytes = FIXTURE_PDF.read_bytes()

    with (
        patch("app.api.main.add_chunks") as mock_store,
        patch("app.api.main.invalidate_index") as mock_invalidate,
    ):
        mock_store.return_value = None
        mock_invalidate.return_value = None

        r = client.post(
            "/ingest",
            files={"files": ("sample_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ingested"
    assert len(body["documents"]) == 1
    doc_result = body["documents"][0]
    assert doc_result["filename"] == "sample_doc.pdf"
    assert doc_result["chunks_created"] > 0
    assert doc_result["pages"] >= 1
    # Verify add_chunks was called with chunks that all have required fields
    assert mock_store.called
    chunks_arg = mock_store.call_args[0][0]
    for chunk in chunks_arg:
        assert chunk["page_number"] is not None
        assert chunk["section_title"]
        assert chunk["chunk_id"]


# ── /query — Phase 2 stub ─────────────────────────────────────────────────────

def test_query_returns_200():
    r = client.post("/query", json={"question": "What is the notice period?"})
    assert r.status_code == 200


def test_query_empty_question_returns_400():
    r = client.post("/query", json={"question": "   "})
    assert r.status_code == 400
