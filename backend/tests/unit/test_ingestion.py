"""
tests/unit/test_ingestion.py — DECISION.md Rule 7, RULES.md "Ingestion Tests".

Tests run against the fixture PDF at tests/fixtures/sample_doc.pdf.
The fixture is checked in for CI reproducibility and matches the
content in tests/fixtures/create_fixture_pdf.py.

Required by RULES.md:
  - test_every_chunk_has_page_number
  - test_every_chunk_has_section_title
  - test_chunk_size_within_target_range
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.ingest.chunker import chunk_document

FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "sample_doc.pdf"


@pytest.fixture(scope="module")
def chunks():
    """Chunk the fixture PDF once for all tests in this module."""
    if not FIXTURE_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {FIXTURE_PDF}")
    return chunk_document(str(FIXTURE_PDF))


# ── RULES.md required tests ───────────────────────────────────────────────────

def test_every_chunk_has_page_number(chunks):
    """RULES.md: test_every_chunk_has_page_number"""
    assert len(chunks) > 0, "No chunks produced — ingestion likely failed silently."
    for c in chunks:
        assert c.get("page_number") is not None, f"Chunk missing page_number: {c}"
        assert isinstance(c["page_number"], int), f"page_number must be int: {c}"
        assert c["page_number"] >= 1, f"page_number must be >= 1 (1-indexed): {c}"


def test_every_chunk_has_section_title(chunks):
    """RULES.md: test_every_chunk_has_section_title"""
    for c in chunks:
        assert c.get("section_title"), f"Chunk missing section_title: {c}"
        assert isinstance(c["section_title"], str), f"section_title must be str: {c}"
        assert len(c["section_title"].strip()) > 0, f"section_title must not be blank: {c}"


def test_chunk_size_within_target_range(chunks):
    """
    RULES.md: test_chunk_size_within_target_range
    DECISION.md Rule 8: chunk should be a plausible citation unit.
    Bounds: 15-400 words.
    """
    for c in chunks:
        word_count = len(c["text"].split())
        assert 15 <= word_count <= 400, (
            f"Chunk word count {word_count} outside 15-400 range "
            f"(page {c.get('page_number')}, section '{c.get('section_title')}')"
        )


# ── Additional ingestion invariants ──────────────────────────────────────────

def test_every_chunk_has_chunk_id(chunks):
    """chunk_id must be present and unique."""
    seen = set()
    for c in chunks:
        assert c.get("chunk_id"), f"Chunk missing chunk_id: {c}"
        assert c["chunk_id"] not in seen, f"Duplicate chunk_id: {c['chunk_id']}"
        seen.add(c["chunk_id"])


def test_every_chunk_has_source_file(chunks):
    """source_file must be present on every chunk."""
    for c in chunks:
        assert c.get("source_file"), f"Chunk missing source_file: {c}"


def test_every_chunk_has_text(chunks):
    """text must be present and non-empty on every chunk."""
    for c in chunks:
        assert c.get("text"), f"Chunk missing text: {c}"
        assert len(c["text"].strip()) > 0, f"Chunk text is blank: {c}"


# ── Error path tests (API.md 400 / 422 contract) ──────────────────────────────

def test_unsupported_file_type_raises_value_error():
    """
    Chunker must raise ValueError for non-PDF files.
    API.md: POST /ingest returns 400 for unsupported file types.
    """
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        tmp_path = f.name
    try:
        with pytest.raises(ValueError, match="Unsupported file type"):
            chunk_document(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_empty_pdf_raises_value_error():
    """
    A PDF with no extractable text must raise ValueError.
    API.md: POST /ingest returns 422 for unparseable files.
    """
    import fitz

    doc = fitz.open()
    doc.new_page()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()
    try:
        with pytest.raises(ValueError, match="no extractable text"):
            chunk_document(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_nonexistent_file_raises_file_not_found_error():
    """Chunker must raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        chunk_document("/tmp/does_not_exist_xyz.pdf")


# ── POST /ingest endpoint tests ───────────────────────────────────────────────

def test_ingest_endpoint_returns_400_for_non_pdf():
    """API.md: POST /ingest returns 400 for unsupported file type."""
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    response = client.post(
        "/ingest",
        files=[("files", ("test.txt", b"hello world", "text/plain"))],
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_ingest_endpoint_returns_422_for_empty_pdf():
    """API.md: POST /ingest returns 422 for a PDF with no extractable text."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    try:
        with open(tmp_path, "rb") as pdf_file:
            response = client.post(
                "/ingest",
                files=[("files", ("blank.pdf", pdf_file, "application/pdf"))],
            )
        assert response.status_code == 422
    finally:
        os.unlink(tmp_path)


def test_ingest_endpoint_success_with_fixture_pdf():
    """
    POST /ingest with the fixture PDF must return status=ingested
    with chunk counts > 0 and pages > 0.
    """
    if not FIXTURE_PDF.exists():
        pytest.skip("Fixture PDF not found")

    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    with open(FIXTURE_PDF, "rb") as f:
        response = client.post(
            "/ingest",
            files=[("files", ("sample_doc.pdf", f, "application/pdf"))],
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ingested"
    assert len(body["documents"]) == 1
    doc = body["documents"][0]
    assert doc["filename"] == "sample_doc.pdf"
    assert doc["chunks_created"] > 0
    assert doc["pages"] > 0


# ── Phase E: Size limit + session append + invalid session_id ─────────────────

def test_upload_over_10mb_returns_413_before_parsing():
    """
    POST /ingest with a file > 10 MB must return 413 BEFORE any PDF parsing.
    Verifies that MAX_FILE_SIZE_BYTES = 10MB constant is honoured and that
    PyMuPDF is never invoked (we send raw bytes that are not a valid PDF).
    Renamed from the old 50MB version; limit lowered per SIZE-LIMIT-AND-APPEND-CHANGE.md.
    """
    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    # 11 MB of zeros — NOT a valid PDF, but we must never reach parsing
    oversized_bytes = b"\x00" * (11 * 1024 * 1024)
    response = client.post(
        "/ingest",
        files=[("files", ("big.pdf", oversized_bytes, "application/pdf"))],
    )
    assert response.status_code == 413
    detail = response.json()["detail"]
    assert "10 MB" in detail or "limit" in detail.lower()


def test_ingest_with_existing_session_id_appends_documents():
    """
    POST /ingest with a valid existing session_id must append documents
    to that session rather than creating a new one.  Verified by ingesting
    the same fixture PDF twice with the same session_id and confirming
    the returned session_id is unchanged and both ingest calls succeed.

    Requires live Qdrant — skipped automatically when Qdrant is unreachable.
    """
    if not FIXTURE_PDF.exists():
        pytest.skip("Fixture PDF not found")

    # Skip if Qdrant is not reachable (live-infra gate)
    try:
        import socket
        from app.shared.config import get_settings
        settings = get_settings()
        host = settings.qdrant_endpoint or "localhost"
        # Quick TCP probe — if this fails, Qdrant is not running
        import urllib.parse
        parsed = urllib.parse.urlparse(host if "://" in host else f"http://{host}")
        s = socket.create_connection((parsed.hostname or "localhost", parsed.port or 6333), timeout=2)
        s.close()
    except Exception:
        pytest.skip("Qdrant not reachable — skipping live append test")

    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)

    # First ingest — no session_id supplied; backend mints one
    with open(FIXTURE_PDF, "rb") as f:
        resp1 = client.post(
            "/ingest",
            files=[("files", ("sample_doc.pdf", f, "application/pdf"))],
        )
    assert resp1.status_code == 200
    body1 = resp1.json()
    session_id = body1["session_id"]
    assert session_id, "Backend must return a session_id on first ingest"
    assert len(body1["documents"]) == 1

    # Second ingest — same session_id (append mode)
    with open(FIXTURE_PDF, "rb") as f:
        resp2 = client.post(
            "/ingest",
            files=[("files", ("sample_doc_copy.pdf", f, "application/pdf"))],
            data={"session_id": session_id},
        )
    assert resp2.status_code == 200
    body2 = resp2.json()
    # session_id must be the SAME — no new session created
    assert body2["session_id"] == session_id, (
        f"Expected session_id={session_id!r}, got {body2['session_id']!r}"
    )
    # Backend returns only the newly added doc, not cumulative
    assert len(body2["documents"]) == 1
    assert body2["documents"][0]["chunks_created"] > 0


def test_ingest_with_blank_session_id_returns_400():
    """
    POST /ingest with an explicitly blank session_id (non-null but empty/whitespace)
    must return 400 with a useful error shape.
    An *absent* session_id is fine (backend mints one); only a whitespace-only
    value is rejected because callers must not pass empty strings.
    """
    if not FIXTURE_PDF.exists():
        pytest.skip("Fixture PDF not found")

    from fastapi.testclient import TestClient
    from app.api.main import app

    client = TestClient(app)
    with open(FIXTURE_PDF, "rb") as f:
        response = client.post(
            "/ingest",
            files=[("files", ("sample_doc.pdf", f, "application/pdf"))],
            data={"session_id": "   "},  # whitespace-only — invalid
        )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "session_id" in detail.lower() or "blank" in detail.lower()
