"""
fusion.py — Reciprocal Rank Fusion (RRF) for hybrid search.

Combines the ranked results from MongoDB Atlas Search (keyword) and Qdrant (semantic).
"""
from __future__ import annotations

from typing import Any, List


def reciprocal_rank_fusion(
    results_list: List[List[dict[str, Any]]],
    k: int = 60,
    top_k: int = 5,
) -> List[dict[str, Any]]:
    """
    Fuses multiple ranked lists of chunks using Reciprocal Rank Fusion.
    
    score = 1 / (k + rank)
    
    Args:
        results_list: A list of lists of chunk dicts (e.g. [bm25_results, vector_results]).
        k: The constant 'k' used in RRF (default 60 is standard in literature).
        top_k: The number of top chunks to return after fusion.
    """
    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, dict[str, Any]] = {}

    for ranked_list in results_list:
        for rank, chunk in enumerate(ranked_list):
            c_id = chunk["chunk_id"]
            if c_id not in chunk_map:
                # Keep a copy of the chunk to avoid mutating the original
                chunk_map[c_id] = chunk.copy()
            
            # Add RRF score contribution
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + 1.0 / (k + rank + 1)
            
            # Preserve original scores if they exist for debugging/transparency
            if "bm25_score" in chunk:
                chunk_map[c_id]["bm25_score"] = chunk["bm25_score"]
            if "vector_score" in chunk:
                chunk_map[c_id]["vector_score"] = chunk["vector_score"]

    # Sort all seen chunks by their fused RRF score
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Take top_k
    fused_results = []
    for c_id, score in sorted_items[:top_k]:
        chunk = chunk_map[c_id]
        chunk["rrf_score"] = score
        fused_results.append(chunk)

    return fused_results
