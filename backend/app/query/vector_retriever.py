"""
vector_retriever.py — semantic search via Chroma (embedded mode).

ARCHITECTURE.md retrieval flow:
  BM25 top-k candidates -> BGE-small embed -> vector similarity re-rank
  -> [optional] NVIDIA Build rerank -> LLM -> citation_verifier

This module handles the vector similarity step against the Chroma
collection created by store.py. It runs entirely in-process — no
external service call.
"""
from __future__ import annotations

from typing import Any, List


def vector_search(
    query: str,
    top_k: int = 10,
    session_id: str | None = None,
) -> List[dict[str, Any]]:
    """
    Search for the top_k most semantically similar chunks to `query`.

    Returns a list of chunk dicts annotated with `vector_score`
    (cosine similarity, 0-1, higher is better).

    Args:
        query: the user's question
        top_k: max results to return
        session_id: if provided, filter to only chunks from this session
    """
    if not query.strip():
        return []

    from app.ingest.embed_service import embed_query
    from app.ingest.store import _get_collection

    query_vec = embed_query(query)
    collection = _get_collection()

    # Build where filter for session scoping
    where = {"session_id": session_id} if session_id else None

    try:
        result = collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
            where=where,
        )
    except Exception as exc:
        print(f"[vector] Chroma query error: {exc}")
        return []

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    chunks = []
    for chunk_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        # Chroma returns cosine distance (0 = identical, 2 = opposite).
        # Convert to similarity: similarity = 1 - distance (for normalized vectors).
        similarity = max(0.0, 1.0 - dist)
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "source_file": meta.get("source_file"),
            "vector_score": similarity,
        })

    return chunks
