"""
chunker.py — splits a PDF into chunks by page + heading.

DECISION.md Rule 7: Every chunk MUST have non-null page_number and
section_title. If headings cannot be reliably detected, fall back to
"Untitled section, page N" — never null.

Returns a list of dicts:
  {
    "chunk_id": str,       # unique: "{filename_stem}_p{page}_c{idx}"
    "text": str,           # the chunk's raw text
    "page_number": int,    # 1-indexed
    "section_title": str,  # heading detected or fallback
    "source_file": str,    # original filename
  }
"""

import re
import hashlib
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


# ── Heading-detection heuristics ────────────────────────────────────────────
# We look at font size, bold flags, and short-line length to classify headings.
# Thresholds tuned for typical policy/report PDFs with clear heading hierarchy.

_HEADING_MIN_FONT_SIZE_RATIO = 1.15  # heading is >= 15% larger than body median
_MIN_BODY_FONT_SIZE = 9.0            # anything smaller is footer/caption, skip
_MAX_HEADING_WORDS = 20              # long lines are body text, not headings
_CHUNK_TARGET_WORDS = (50, 350)      # DECISION.md Rule 8 plausible citation unit


def _median_font_size(page: fitz.Page) -> float:
    """Return the median font size on a page (proxy for body text size)."""
    sizes = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span["size"]
                if sz >= _MIN_BODY_FONT_SIZE:
                    sizes.append(sz)
    if not sizes:
        return 12.0
    sizes.sort()
    return sizes[len(sizes) // 2]


def _is_heading(span_text: str, font_size: float, flags: int, median_fs: float) -> bool:
    """Heuristic: is this text span a section heading?"""
    text = span_text.strip()
    if not text:
        return False
    word_count = len(text.split())
    if word_count > _MAX_HEADING_WORDS:
        return False
    is_bold = bool(flags & 2**4)  # PyMuPDF bold flag
    is_larger = font_size >= median_fs * _HEADING_MIN_FONT_SIZE_RATIO
    looks_like_heading = is_bold or is_larger
    return looks_like_heading


def _extract_page_lines(page: fitz.Page) -> list[dict]:
    """
    Extract lines from a page with metadata.
    Returns list of {"text": str, "font_size": float, "flags": int, "is_heading": bool}
    """
    median_fs = _median_font_size(page)
    lines_out = []

    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            line_texts = []
            max_font_size = 0.0
            flags = 0
            for span in line.get("spans", []):
                if span["size"] < _MIN_BODY_FONT_SIZE:
                    continue
                line_texts.append(span["text"])
                if span["size"] > max_font_size:
                    max_font_size = span["size"]
                    flags = span["flags"]
            text = " ".join(line_texts).strip()
            if not text:
                continue
            heading = _is_heading(text, max_font_size, flags, median_fs)
            lines_out.append({
                "text": text,
                "font_size": max_font_size,
                "flags": flags,
                "is_heading": heading,
            })
    return lines_out


def _chunk_page_lines(
    page_lines: list[dict],
    page_number: int,
    current_section: str,
) -> tuple[list[dict], str]:
    """
    Convert page lines into text chunks, splitting on heading boundaries.
    Returns (chunks_for_page, updated_current_section).
    """
    chunks: list[dict] = []
    buffer: list[str] = []
    section = current_section

    def flush(buf: list[str], sec: str) -> dict | None:
        text = " ".join(buf).strip()
        # Collapse excessive whitespace
        text = re.sub(r"\s+", " ", text)
        if len(text.split()) < 10:  # skip near-empty fragments
            return None
        return {"text": text, "section_title": sec, "page_number": page_number}

    for line in page_lines:
        if line["is_heading"]:
            # Flush previous buffer as a chunk
            if buffer:
                chunk = flush(buffer, section)
                if chunk:
                    chunks.append(chunk)
                buffer = []
            section = line["text"]
        else:
            buffer.append(line["text"])

            # Hard size cap: if we're already huge, flush now
            if len(" ".join(buffer).split()) >= _CHUNK_TARGET_WORDS[1]:
                chunk = flush(buffer, section)
                if chunk:
                    chunks.append(chunk)
                buffer = []

    # Flush remaining buffer
    if buffer:
        chunk = flush(buffer, section)
        if chunk:
            chunks.append(chunk)

    return chunks, section


def chunk_document(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Main entry point. Chunks a PDF file and returns a list of chunk dicts.

    Raises:
        ValueError: if the file is not a PDF or produces zero extractable text.
        FileNotFoundError: if the file doesn't exist.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported file type: {path.suffix}. Only .pdf accepted.")

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise ValueError(f"Could not open PDF '{path.name}': {exc}") from exc

    stem = path.stem
    all_chunks: list[dict] = []
    current_section = f"Introduction"  # default before first heading
    total_text_chars = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_number = page_idx + 1  # 1-indexed

        page_lines = _extract_page_lines(page)
        page_text = " ".join(l["text"] for l in page_lines)
        total_text_chars += len(page_text)

        page_chunks, current_section = _chunk_page_lines(
            page_lines, page_number, current_section
        )

        # DECISION.md Rule 7 enforcement: guarantee section_title is never null
        for chunk in page_chunks:
            if not chunk.get("section_title"):
                chunk["section_title"] = f"Untitled section, page {page_number}"

        all_chunks.extend(page_chunks)

    doc.close()

    # If the entire PDF produced zero text (scanned image / corrupt),
    # raise so the API returns 422 instead of silently ingesting nothing.
    if total_text_chars < 50:
        raise ValueError(
            f"PDF '{path.name}' contains no extractable text. "
            "Possibly a scanned image — use an OCR preprocessor first."
        )

    # Assign stable chunk IDs
    for idx, chunk in enumerate(all_chunks):
        chunk["chunk_id"] = f"{stem}_p{chunk['page_number']:04d}_c{idx:04d}"
        chunk["source_file"] = path.name
        # Final Rule 7 double-check (defensive)
        assert chunk["page_number"] is not None
        assert chunk["section_title"]

    return all_chunks
