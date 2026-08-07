"""
store.py — MongoDB Atlas + Qdrant Cloud vector store integration.

Architecture:
- MongoDB Atlas: Primary database for chunk text, metadata, and BM25 (Atlas Search).
- Qdrant Cloud: Vector database storing ONLY embeddings + minimal metadata.

DECISION.md Rule 7: Every chunk MUST have non-null page_number and section_title.
"""
from __future__ import annotations

import uuid
from typing import Any, List

from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.ingest.embed_service import embed_texts
from app.shared.config import get_mongo_client, get_qdrant_client, MONGODB_DB

COLLECTION_NAME = "document_chunks"


def _init_qdrant_collection() -> None:
    """Ensure Qdrant collection exists."""
    qdrant = get_qdrant_client()
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )


def _get_qdrant_id(chunk_id: str) -> str:
    """Hash string chunk_id into a stable UUID for Qdrant."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def add_chunks(chunks: List[dict[str, Any]], session_id: str | None = None) -> None:
    """
    Embed and upsert a list of chunk dicts into MongoDB and Qdrant.

    Each chunk must have: chunk_id, text, page_number, section_title, source_file.
    """
    if not chunks:
        return

    _init_qdrant_collection()
    
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)  # List[List[float]]

    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    mongo_collection = db["chunks"]

    qdrant = get_qdrant_client()
    points = []
    mongo_docs = []

    for chunk, embedding in zip(chunks, embeddings):
        qdrant_id = _get_qdrant_id(chunk["chunk_id"])
        
        # 1. Prepare Qdrant Point (Payload has NO text)
        payload = {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
        }
        if session_id:
            payload["session_id"] = session_id

        points.append(
            PointStruct(
                id=qdrant_id,
                vector=embedding,
                payload=payload,
            )
        )
        
        # 2. Prepare MongoDB Document
        doc = {
            "_id": chunk["chunk_id"],  # use chunk_id as primary key
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "text": chunk["text"],
        }
        if session_id:
            doc["session_id"] = session_id
        mongo_docs.append(doc)

    # Upsert to Qdrant
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    # Upsert to MongoDB (Bulk Write)
    from pymongo import ReplaceOne
    operations = [
        ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
        for doc in mongo_docs
    ]
    if operations:
        mongo_collection.bulk_write(operations)


def get_all_chunks() -> List[dict[str, Any]]:
    """Return all stored chunks (used by legacy tests or BM25 fallback)."""
    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    cursor = db["chunks"].find({})
    
    return [
        {
            "chunk_id": doc["chunk_id"],
            "source_file": doc["source_file"],
            "page_number": doc["page_number"],
            "section_title": doc["section_title"],
            "text": doc["text"],
        }
        for doc in cursor
    ]


def get_chunks_by_ids(ids: List[str]) -> List[dict[str, Any]]:
    """Fetch specific chunks by their chunk_id list from MongoDB."""
    if not ids:
        return []
    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    
    cursor = db["chunks"].find({"_id": {"$in": ids}})
    
    # Preserve order of `ids`
    doc_map = {
        doc["_id"]: {
            "chunk_id": doc["chunk_id"],
            "source_file": doc["source_file"],
            "page_number": doc["page_number"],
            "section_title": doc["section_title"],
            "text": doc["text"],
        }
        for doc in cursor
    }
    
    result = []
    for chunk_id in ids:
        if chunk_id in doc_map:
            result.append(doc_map[chunk_id])
            
    return result


def reset_collection() -> None:
    """Drop the collections — used in tests only."""
    # Reset Qdrant
    qdrant = get_qdrant_client()
    if qdrant.collection_exists(COLLECTION_NAME):
        qdrant.delete_collection(COLLECTION_NAME)
        
    # Reset MongoDB
    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    db["chunks"].drop()
