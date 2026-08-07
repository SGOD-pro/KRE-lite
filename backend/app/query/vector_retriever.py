"""
vector_retriever.py — semantic search via Qdrant Cloud.

Retrieves top chunks from Qdrant by cosine similarity, then fetches the raw text
and metadata from MongoDB Atlas.
"""
from __future__ import annotations

from typing import Any, List

from app.ingest.embed_service import embed_query
from app.ingest.store import get_chunks_by_ids, COLLECTION_NAME
from app.shared.config import get_qdrant_client


def vector_search(
    query: str,
    top_k: int = 10,
) -> List[dict[str, Any]]:
    """
    Search Qdrant for semantic similarity to `query`.
    Returns list of chunks (with text from Mongo), annotated with `vector_score`.
    """
    if not query.strip():
        return []

    query_vec = embed_query(query)

    qdrant = get_qdrant_client()
    try:
        search_result = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vec,
            limit=top_k,
        ).points
    except Exception as e:
        print(f"Qdrant search error: {e}")
        return []

    if not search_result:
        return []

    # search_result contains ScoredPoint objects with .id, .score, .payload
    chunk_ids = [hit.payload["chunk_id"] for hit in search_result if "chunk_id" in hit.payload]
    
    # Fetch from Mongo
    mongo_chunks = get_chunks_by_ids(chunk_ids)
    
    # Map by chunk_id to reconstruct order and attach scores
    mongo_map = {c["chunk_id"]: c for c in mongo_chunks}
    
    scored_chunks = []
    for hit in search_result:
        c_id = hit.payload.get("chunk_id")
        if c_id and c_id in mongo_map:
            chunk = mongo_map[c_id].copy()
            chunk["vector_score"] = hit.score
            scored_chunks.append(chunk)

    return scored_chunks
