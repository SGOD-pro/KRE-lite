"""
Ingestion tests — DECISION.md Rule 7, RULES.md "Ingestion Tests".

Point TEST_PDF_PATH at a small real PDF in your demo document set
once chosen (MEMORY.md "Hour 0" entry) or a small fixture PDF checked
into tests/fixtures/ for CI reproducibility — don't rely on a file
that only exists on a developer's machine.
"""
import pytest

from app.ingest.chunker import chunk_document

TEST_PDF_PATH = "tests/fixtures/sample_doc.pdf"  # REPLACE / add fixture


@pytest.fixture(scope="module")
def chunks():
    return chunk_document(TEST_PDF_PATH)


def test_every_chunk_has_page_number(chunks):
    assert len(chunks) > 0, "No chunks produced — ingestion likely failed silently."
    for c in chunks:
        assert c.get("page_number") is not None, f"Chunk missing page_number: {c}"


def test_every_chunk_has_section_title(chunks):
    for c in chunks:
        assert c.get("section_title"), f"Chunk missing section_title: {c}"


def test_chunk_size_within_target_range(chunks):
    # Rough sanity bounds per DECISION.md Rule 8 — a chunk should be a
    # plausible citation unit: not a single sentence, not a full page
    # dump. Adjust bounds once you've looked at real output, but keep
    # this test — it catches a broken chunker early.
    for c in chunks:
        word_count = len(c["text"].split())
        assert 15 <= word_count <= 400, (
            f"Chunk word count {word_count} outside expected range "
            f"(page {c.get('page_number')}, section {c.get('section_title')})"
        )
