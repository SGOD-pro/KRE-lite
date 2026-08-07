"""
test_ingestion.py — DECISION.md Rule 7, RULES.md "Ingestion Tests".

Tests run against a generated fixture PDF (created by tests/fixtures/create_fixture_pdf.py).
The fixture is checked in as sample_doc.pdf for CI reproducibility.
"""
import sys
from pathlib import Path

# Ensure backend root is importable
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from app.ingest.chunker import chunk_document

FIXTURE_PDF = Path(__file__).parent / "tests" / "fixtures" / "sample_doc.pdf"


@pytest.fixture(scope="module")
def chunks():
    if not FIXTURE_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {FIXTURE_PDF}. Run create_fixture_pdf.py first.")
    return chunk_document(str(FIXTURE_PDF))


def test_every_chunk_has_page_number(chunks):
    assert len(chunks) > 0, "No chunks produced — ingestion likely failed silently."
    for c in chunks:
        assert c.get("page_number") is not None, f"Chunk missing page_number: {c}"
        assert isinstance(c["page_number"], int), f"page_number must be int: {c}"
        assert c["page_number"] >= 1, f"page_number must be 1-indexed >= 1: {c}"


def test_every_chunk_has_section_title(chunks):
    for c in chunks:
        assert c.get("section_title"), f"Chunk missing section_title: {c}"
        assert isinstance(c["section_title"], str), f"section_title must be str: {c}"
        assert len(c["section_title"].strip()) > 0, f"section_title is blank: {c}"


def test_chunk_size_within_target_range(chunks):
    """
    DECISION.md Rule 8: chunk should be a plausible citation unit.
    Bounds: 15-400 words. Adjust if real docs push these, but keep the test.
    """
    for c in chunks:
        word_count = len(c["text"].split())
        assert 15 <= word_count <= 400, (
            f"Chunk word count {word_count} outside expected range "
            f"(page {c.get('page_number')}, section {c.get('section_title')})"
        )


def test_every_chunk_has_chunk_id(chunks):
    """chunk_id must be present and unique."""
    seen_ids = set()
    for c in chunks:
        assert c.get("chunk_id"), f"Chunk missing chunk_id: {c}"
        assert c["chunk_id"] not in seen_ids, f"Duplicate chunk_id: {c['chunk_id']}"
        seen_ids.add(c["chunk_id"])


def test_every_chunk_has_source_file(chunks):
    for c in chunks:
        assert c.get("source_file"), f"Chunk missing source_file: {c}"


def test_unsupported_file_type_raises_value_error():
    """Chunker must raise ValueError for non-PDF files (API returns 400)."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        tmp_path = f.name
    try:
        with pytest.raises(ValueError, match="Unsupported file type"):
            chunk_document(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_empty_pdf_raises_value_error():
    """A PDF with no text must raise ValueError (API returns 422)."""
    import fitz, tempfile, os
    # Create a PDF with only a blank page (no text)
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
