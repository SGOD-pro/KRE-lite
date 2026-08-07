"""
store.py — Vector store (Qdrant) + Document store (MongoDB Atlas).

Architecture:
- Qdrant: Stores 1024-dim Titan embeddings and payload for fast similarity search.
- MongoDB Atlas: Primary document store for full chunk text and metadata.

DECISION.md Rule 7: Every chunk MUST have non-null page_number and section_title.
"""
from __future__ import annotations

import uuid
from typing import Any, List

from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.ingest.embed_service import EMBEDDING_DIM, embed_texts
from app.shared.config import get_mongo_client, get_qdrant_client, MONGODB_DB

COLLECTION_NAME = "document_chunks"


def _init_qdrant_collection() -> None:
    """Ensure Qdrant collection and payload indexes exist."""
    qdrant = get_qdrant_client()
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
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
    """Deterministic UUID5 for Qdrant point IDs."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def add_chunks(chunks: List[dict[str, Any]], session_id: str | None = None) -> None:
    """
    Embed chunks using Bedrock Titan and store in Qdrant + MongoDB Atlas.
    Enforces DECISION.md Rule 7 (page_number and section_title cannot be null).
    """
    if not chunks:
        return

    # Validate Rule 7 upfront
    for c in chunks:
        if not c.get("page_number"):
            raise ValueError(f"DECISION.md Rule 7 violation: chunk missing page_number: {c.get('chunk_id')}")
        if not c.get("section_title"):
            raise ValueError(f"DECISION.md Rule 7 violation: chunk missing section_title: {c.get('chunk_id')}")

    _init_qdrant_collection()

    texts = [c["text"] for c in chunks]
    print(f"[store] Embedding {len(chunks)} chunks via Bedrock Titan...")
    embeddings = embed_texts(texts)

    qdrant = get_qdrant_client()
    points: List[PointStruct] = []
    mongo_docs: List[dict[str, Any]] = []

    for chunk, embedding in zip(chunks, embeddings):
        qdrant_id = _get_qdrant_id(chunk["chunk_id"])

        payload = {
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk.get("source_file", ""),
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "text": chunk["text"],
            "session_id": session_id or "",
        }
        points.append(PointStruct(id=qdrant_id, vector=embedding, payload=payload))

        doc = {
            "_id": chunk["chunk_id"],
            "chunk_id": chunk["chunk_id"],
            "source_file": chunk.get("source_file", ""),
            "page_number": chunk["page_number"],
            "section_title": chunk["section_title"],
            "text": chunk["text"],
            "session_id": session_id or "",
        }
        mongo_docs.append(doc)

    # Upsert to Qdrant in batches
    batch_size = 50
    for i in range(0, len(points), batch_size):
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i:i + batch_size],
        )

    # Upsert to MongoDB
    try:
        from pymongo import ReplaceOne
        mongo = get_mongo_client()
        db = mongo[MONGODB_DB]
        mongo_collection = db["chunks"]
        operations = [
            ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
            for doc in mongo_docs
        ]
        if operations:
            mongo_collection.bulk_write(operations)
    except Exception as exc:
        print(f"[store] Mongo write warning: {exc}")

    print(f"[store] Stored {len(chunks)} chunks in Qdrant and MongoDB [OK]")


def get_all_chunks(session_id: str | None = None) -> List[dict[str, Any]]:
    """
    Retrieve all stored chunks (used by BM25 retriever).
    Attempts MongoDB first, falls back to Qdrant if MongoDB is unreachable.
    """
    try:
        mongo = get_mongo_client()
        db = mongo[MONGODB_DB]
        filter_query = {"session_id": session_id} if session_id else {}
        cursor = db["chunks"].find(filter_query)
        chunks = [
            {
                "chunk_id": doc["chunk_id"],
                "source_file": doc.get("source_file", ""),
                "page_number": doc["page_number"],
                "section_title": doc["section_title"],
                "text": doc["text"],
                "session_id": doc.get("session_id"),
            }
            for doc in cursor
        ]
        if chunks:
            return chunks
    except Exception as exc:
        print(f"[store] Mongo read warning: {exc}")

    # Fallback to Qdrant payload scroll
    try:
        qdrant = get_qdrant_client()
        _init_qdrant_collection()
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue
        scroll_filter = None
        if session_id:
            scroll_filter = Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])

        records, _ = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        return [
            {
                "chunk_id": r.payload["chunk_id"],
                "source_file": r.payload.get("source_file", ""),
                "page_number": r.payload["page_number"],
                "section_title": r.payload["section_title"],
                "text": r.payload["text"],
                "session_id": r.payload.get("session_id"),
            }
            for r in records
            if r.payload and "chunk_id" in r.payload and "text" in r.payload
        ]
    except Exception as exc:
        print(f"[store] Qdrant scroll warning: {exc}")
        return []


def get_chunks_by_ids(ids: List[str]) -> List[dict[str, Any]]:
    """Fetch specific chunks by their chunk_ids."""
    if not ids:
        return []

    try:
        mongo = get_mongo_client()
        db = mongo[MONGODB_DB]
        cursor = db["chunks"].find({"_id": {"$in": ids}})
        doc_map = {
            doc["_id"]: {
                "chunk_id": doc["chunk_id"],
                "source_file": doc.get("source_file", ""),
                "page_number": doc["page_number"],
                "section_title": doc["section_title"],
                "text": doc["text"],
            }
            for doc in cursor
        }
        result = [doc_map[cid] for cid in ids if cid in doc_map]
        if result:
            return result
    except Exception as exc:
        print(f"[store] Mongo get_chunks warning: {exc}")

    # Fallback to Qdrant
    try:
        qdrant = get_qdrant_client()
        from qdrant_client.http.models import FieldCondition, Filter, MatchAny
        points = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=[FieldCondition(key="chunk_id", match=MatchAny(any=ids))]),
            limit=len(ids),
            with_payload=True,
            with_vectors=False,
        )[0]
        q_map = {
            p.payload["chunk_id"]: {
                "chunk_id": p.payload["chunk_id"],
                "source_file": p.payload.get("source_file", ""),
                "page_number": p.payload["page_number"],
                "section_title": p.payload["section_title"],
                "text": p.payload["text"],
            }
            for p in points
            if p.payload and "chunk_id" in p.payload
        }
        return [q_map[cid] for cid in ids if cid in q_map]
    except Exception as exc:
        print(f"[store] Qdrant get_chunks warning: {exc}")
        return []


def reset_collection(session_id: str | None = None) -> None:
    """Reset / clear chunks from Qdrant and MongoDB."""
    qdrant = get_qdrant_client()
    mongo = get_mongo_client()
    db = mongo[MONGODB_DB]

    if session_id:
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue
        try:
            qdrant.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]),
            )
        except Exception:
            pass
        try:
            db["chunks"].delete_many({"session_id": session_id})
        except Exception:
            pass
    else:
        try:
            if qdrant.collection_exists(COLLECTION_NAME):
                qdrant.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        try:
            db["chunks"].drop()
        except Exception:
            pass
