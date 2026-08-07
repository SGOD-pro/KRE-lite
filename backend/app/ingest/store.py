"""
store.py — MongoDB Atlas + Qdrant Cloud vector store integration.

Architecture:
- MongoDB Atlas: Primary database for chunk text, metadata, and BM25 (Atlas Search).
- Qdrant Cloud: Vector database storing ONLY embeddings + minimal metadata.

Two-Phase Ingestion:
  Phase 1 — add_chunks_without_embedding(): store chunks in MongoDB only (fast).
  Phase 2 — embed_and_upsert_session():     embed from MongoDB + upsert to Qdrant (slow, rate-limited).

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
    """Ensure Qdrant collection and payload indexes exist."""
    qdrant = get_qdrant_client()
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
    try:
        from qdrant_client.http import models
        qdrant.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="session_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass


def _get_qdrant_id(chunk_id: str) -> str:
    """Hash string chunk_id into a stable UUID for Qdrant."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def add_chunks_without_embedding(chunks: List[dict[str, Any]], session_id: str | None = None) -> None:
    """
    Phase 1: Store chunks in MongoDB ONLY — no embeddings.
    Sets 'embedded': False so Phase 2 knows which chunks to process.
    """
    if not chunks:
        return

    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    mongo_collection = db["chunks"]

    mongo_docs = []
    for chunk in chunks:
        doc = {
            "_id": chunk["chunk_id"],
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "text": chunk["text"],
            "embedded": False,  # Phase 2 will flip this to True
        }
        if session_id:
            doc["session_id"] = session_id
        mongo_docs.append(doc)

    from pymongo import ReplaceOne
    operations = [
        ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
        for doc in mongo_docs
    ]
    if operations:
        mongo_collection.bulk_write(operations)

    print(f"[store] Saved {len(mongo_docs)} chunks to MongoDB (not yet embedded)")


def embed_and_upsert_session(session_id: str) -> int:
    """
    Phase 2: Fetch all un-embedded chunks for a session from MongoDB,
    embed with Bedrock (1.4s sleep per chunk), and upsert to Qdrant.
    Returns the number of chunks embedded.
    """
    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    mongo_collection = db["chunks"]

    # Fetch only un-embedded chunks for this session
    cursor = mongo_collection.find({
        "session_id": session_id,
        "embedded": {"$ne": True},
    })
    chunks = list(cursor)

    if not chunks:
        print(f"[store] No un-embedded chunks found for session '{session_id}'")
        return 0

    print(f"[store] Embedding {len(chunks)} chunks for session '{session_id}' (1.4s/chunk)...")
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    qdrant = get_qdrant_client()
    points = []

    for chunk, embedding in zip(chunks, embeddings):
        qdrant_id = _get_qdrant_id(chunk["chunk_id"])
        payload = {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "session_id": session_id,
        }
        points.append(PointStruct(id=qdrant_id, vector=embedding, payload=payload))

    # Upsert to Qdrant in batches of 50
    batch_size = 50
    for i in range(0, len(points), batch_size):
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i:i + batch_size],
        )

    # Mark chunks as embedded in MongoDB
    chunk_ids = [c["chunk_id"] for c in chunks]
    mongo_collection.update_many(
        {"chunk_id": {"$in": chunk_ids}},
        {"$set": {"embedded": True}},
    )

    print(f"[store] Embedded and upserted {len(points)} vectors to Qdrant [OK]")
    return len(points)


def add_chunks(chunks: List[dict[str, Any]], session_id: str | None = None) -> None:
    """
    Legacy: embed-and-store in one shot (used by legacy tests).
    Prefer add_chunks_without_embedding + embed_and_upsert_session.
    """
    if not chunks:
        return

    _init_qdrant_collection()

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    mongo_collection = db["chunks"]

    qdrant = get_qdrant_client()
    points = []
    mongo_docs = []

    for chunk, embedding in zip(chunks, embeddings):
        qdrant_id = _get_qdrant_id(chunk["chunk_id"])

        payload = {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
        }
        if session_id:
            payload["session_id"] = session_id

        points.append(PointStruct(id=qdrant_id, vector=embedding, payload=payload))

        doc = {
            "_id": chunk["chunk_id"],
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "text": chunk["text"],
            "embedded": True,
        }
        if session_id:
            doc["session_id"] = session_id
        mongo_docs.append(doc)

    batch_size = 50
    for i in range(0, len(points), batch_size):
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i:i + batch_size],
        )

    from pymongo import ReplaceOne
    operations = [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in mongo_docs]
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
    qdrant = get_qdrant_client()
    if qdrant.collection_exists(COLLECTION_NAME):
        qdrant.delete_collection(COLLECTION_NAME)

    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]
    db["chunks"].drop()
