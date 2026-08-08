"""
bm25_retriever.py — Keyword retrieval via rank-bm25 (in-process).

ARCHITECTURE.md: "BM25 (rank-bm25) -> vector search (single index)"

The BM25 index is built lazily from all stored chunks and cached in
memory for the life of the process. Call invalidate_index() after
new chunks are ingested so the next query rebuilds from fresh data.

This keeps the dependency surface minimal — no external Elasticsearch,
no MongoDB Atlas Search index. rank-bm25 is a pure Python library.
"""
from __future__ import annotations

import re
from typing import Any, List

# Module-level cache for the BM25 index and associated chunks
_bm25_index = None
_indexed_chunks: List[dict[str, Any]] = []
_indexed_session: str | None = "__UNSET__"  # sentinel so first call always builds


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


def _build_index(session_id: str | None = None) -> None:
    """Build (or rebuild) the BM25 index from all chunks in the store."""
    global _bm25_index, _indexed_chunks, _indexed_session

    from rank_bm25 import BM25Okapi
    from app.ingest.store import get_all_chunks

    all_chunks = get_all_chunks(session_id=session_id)
    if not all_chunks:
        _bm25_index = None
        _indexed_chunks = []
        _indexed_session = session_id
        return

    tokenized_corpus = [_tokenize(c["text"]) for c in all_chunks]
    _bm25_index = BM25Okapi(tokenized_corpus)
    _indexed_chunks = all_chunks
    _indexed_session = session_id
    print(f"[bm25] Index built: {len(_indexed_chunks)} chunks (session={session_id!r})")


def invalidate_index() -> None:
    """
    Invalidate the cached BM25 index.
    Must be called after new chunks are ingested so the next query
    rebuilds from the updated store.
    """
    global _bm25_index, _indexed_chunks, _indexed_session
    _bm25_index = None
    _indexed_chunks = []
    _indexed_session = "__UNSET__"


def bm25_search(
    query: str,
    top_k: int = 20,
    session_id: str | None = None,
) -> List[dict[str, Any]]:
    """
    Return up to `top_k` chunks ranked by BM25 score.

    Args:
        query: the user's question
        top_k: max results to return
        session_id: if provided, filter to only chunks from this session
    """
    global _bm25_index, _indexed_chunks

    if not query.strip():
        return []

    # Build index on first call, after invalidation, OR when session changes
    if _bm25_index is None or _indexed_session != session_id:
        _build_index(session_id=session_id)

    tokenized_query = _tokenize(query)
    scores = _bm25_index.get_scores(tokenized_query)

    # Pair chunks with scores and sort descending by score with deterministic chunk_id tiebreaker
    scored = sorted(
        zip(_indexed_chunks, scores),
        key=lambda x: (float(x[1]), str(x[0].get("chunk_id", ""))),
        reverse=True,
    )

    results = []
    seen_texts = set()
    for chunk, score in scored:
        if score <= 0:
            break  # BM25 scores of 0 mean no term overlap — not useful
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        text_key = text[:200]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        results.append({**chunk, "bm25_score": float(score)})
        if len(results) >= top_k:
            break

    return results
