"""
bm25_retriever.py — Keyword retrieval via MongoDB Atlas Search.

Uses the built-in `$search` aggregation stage in MongoDB Atlas which leverages
Lucene under the hood for BM25 keyword matching.

NOTE: This requires an Atlas Search index named "default" on the `chunks` collection
mapping the `text` field.
"""
from __future__ import annotations

from typing import Any, List

from app.shared.config import get_mongo_client, MONGODB_DB


def invalidate_index() -> None:
    """
    No-op for MongoDB Atlas Search. 
    The index updates automatically via MongoDB Atlas trigger/sync.
    Kept for compatibility with previous api/main.py logic.
    """
    pass


def bm25_search(query: str, top_k: int = 20, session_id: str | None = None) -> List[dict[str, Any]]:
    """
    Return up to `top_k` chunks ranked by MongoDB Atlas Search score.
    """
    if not query.strip():
        return []

    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    
    search_stage = {
        "$search": {
            "index": "default",
            "text": {
                "query": query,
                "path": "text"
            }
        }
    }
    
    pipeline = [search_stage]
    if session_id:
        pipeline.append({"$match": {"session_id": session_id}})
        
    pipeline.extend([
        {
            "$limit": top_k
        },
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "source_file": 1,
                "page_number": 1,
                "section_title": 1,
                "text": 1,
                "score": {"$meta": "searchScore"}
            }
        }
    ]

    try:
        cursor = db["chunks"].aggregate(pipeline)
        results = []
        for doc in cursor:
            # Re-map "score" to "bm25_score" for consistency with the rest of the app
            score = doc.pop("score", 0.0)
            results.append({**doc, "bm25_score": score})
        return results
    except Exception as e:
        # If the search index doesn't exist, MongoDB throws an error.
        # We catch it so the app doesn't crash entirely.
        print(f"Atlas Search error (is the index created?): {e}")
        return []
