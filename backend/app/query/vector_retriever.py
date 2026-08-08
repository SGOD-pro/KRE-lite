"""
vector_retriever.py — Semantic search via Qdrant and AWS Bedrock Titan Embeddings.

Flow:
1. Query string -> AWS Bedrock Titan embedding (1024-dim).
2. Qdrant vector similarity search against document_chunks collection.
3. Attaches vector_score and returns ranked chunks.
"""
from __future__ import annotations

from typing import Any, List

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.ingest.embed_service import embed_query
from app.ingest.store import COLLECTION_NAME, _init_qdrant_collection, get_chunks_by_ids
from app.shared.config import get_qdrant_client


def vector_search(
    query: str,
    top_k: int = 10,
    session_id: str | None = None,
) -> List[dict[str, Any]]:
    """
    Search Qdrant for chunks semantically similar to `query`.
    """
    if not query.strip():
        return []

    query_vec = embed_query(query)
    qdrant = get_qdrant_client()

    query_filter = None
    if session_id:
        query_filter = Filter(
            must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        )

    fetch_limit = max(top_k * 4, 40)
    try:
        # qdrant-client >= 1.9 query_points API
        search_result = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vec,
            query_filter=query_filter,
            limit=fetch_limit,
            with_payload=True,
        ).points
    except Exception as exc:
        print(f"[vector] Qdrant search error: {exc}")
        return []

    if not search_result:
        return []

    # Map results and attach scores
    scored_chunks = []
    chunk_ids_to_fetch = []

    for hit in search_result:
        payload = hit.payload or {}
        cid = payload.get("chunk_id")
        text = payload.get("text")

        if cid and text:
            # Payload already contains text and metadata
            chunk = {
                "chunk_id": cid,
                "source_file": payload.get("source_file", ""),
                "page_number": payload.get("page_number", 1),
                "section_title": payload.get("section_title", ""),
                "text": text,
                "vector_score": float(hit.score),
                "session_id": payload.get("session_id"),
            }
            scored_chunks.append(chunk)
        elif cid:
            chunk_ids_to_fetch.append((cid, float(hit.score)))

    if chunk_ids_to_fetch:
        c_ids = [c[0] for c in chunk_ids_to_fetch]
        mongo_chunks = get_chunks_by_ids(c_ids)
        mongo_map = {c["chunk_id"]: c for c in mongo_chunks}
        for cid, score in chunk_ids_to_fetch:
            if cid in mongo_map:
                chunk = mongo_map[cid].copy()
                chunk["vector_score"] = score
                scored_chunks.append(chunk)

    # Deterministic tiebreaker: sort descending by vector_score, then chunk_id
    scored_chunks.sort(
        key=lambda x: (x.get("vector_score", 0.0), str(x.get("chunk_id", ""))),
        reverse=True,
    )

    # Deduplicate identical chunks (prevents multi-session duplicate flooding)
    deduped_results = []
    seen_texts = set()
    for chunk in scored_chunks:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        text_key = text[:200]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)
        deduped_results.append(chunk)
        if len(deduped_results) >= top_k:
            break

    return deduped_results
