"""
store.py — Chroma embedded vector store + in-process chunk store.

ARCHITECTURE.md: "Local Chroma or SQLite+sqlite-vec for the demo."
Decision: Chroma in embedded mode (no Docker service, no network hop).

Chunk storage model:
- Chroma collection: stores embeddings + metadata (page, section, chunk_id, source_file)
- In-memory dict (backed by Chroma metadata): stores full chunk text
  for BM25 and retrieval. Chroma documents field holds the text.

All data is persisted to CHROMA_PERSIST_DIR on disk so ingestion
survives app restarts during the demo.

DECISION.md Rule 7: Every chunk has non-null page_number and section_title.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List

# Chroma persist path — configurable via env var, defaults to ./chroma_db/
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PATH", str(Path(__file__).parent.parent.parent / "chroma_db"))
COLLECTION_NAME = "document_chunks"


def _get_client():
    """Return a persistent Chroma client (lazy, cached per-process via module-level singleton)."""
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def _get_collection():
    """Return (or create) the Chroma collection for document chunks."""
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: List[dict[str, Any]], session_id: str | None = None) -> None:
    """
    Embed and store chunks in Chroma.

    Each chunk must have: chunk_id, text, page_number, section_title, source_file.
    DECISION.md Rule 7: enforced — chunk_id without page_number or section_title is rejected.

    Args:
        chunks: list of chunk dicts from chunker.py
        session_id: optional tag for filtering during retrieval
    """
    if not chunks:
        return

    # Validate Rule 7 before doing any embedding work
    for c in chunks:
        if not c.get("page_number"):
            raise ValueError(f"DECISION.md Rule 7 violation: chunk missing page_number: {c.get('chunk_id')}")
        if not c.get("section_title"):
            raise ValueError(f"DECISION.md Rule 7 violation: chunk missing section_title: {c.get('chunk_id')}")

    from app.ingest.embed_service import embed_texts

    texts = [c["text"] for c in chunks]
    print(f"[store] Embedding {len(chunks)} chunks via BGE-small (local)...")
    embeddings = embed_texts(texts)
    print(f"[store] Embedding done.")

    collection = _get_collection()

    ids = [c["chunk_id"] for c in chunks]
    metadatas = [
        {
            "page_number": c["page_number"],
            "section_title": c["section_title"],
            "source_file": c["source_file"],
            "session_id": session_id or "",
        }
        for c in chunks
    ]

    # Upsert in batches to avoid memory spikes on large docs
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.upsert(
            ids=ids[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            documents=texts[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )

    print(f"[store] Upserted {len(chunks)} chunks to Chroma [OK]")


def get_all_chunks(session_id: str | None = None) -> List[dict[str, Any]]:
    """
    Return all stored chunks (used by BM25 retriever to build its index).
    Optionally filter by session_id.
    """
    collection = _get_collection()

    where = {"session_id": session_id} if session_id else None

    try:
        result = collection.get(
            include=["documents", "metadatas"],
            where=where,
        )
    except Exception:
        # Collection might be empty on first call before any ingestion
        result = {"ids": [], "documents": [], "metadatas": []}

    chunks = []
    for chunk_id, text, meta in zip(
        result.get("ids", []),
        result.get("documents", []),
        result.get("metadatas", []),
    ):
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "source_file": meta.get("source_file"),
            "session_id": meta.get("session_id") or None,
        })
    return chunks


def get_chunks_by_ids(ids: List[str]) -> List[dict[str, Any]]:
    """Fetch specific chunks by their chunk_id list."""
    if not ids:
        return []
    collection = _get_collection()
    result = collection.get(
        ids=ids,
        include=["documents", "metadatas"],
    )
    chunks = []
    for chunk_id, text, meta in zip(
        result.get("ids", []),
        result.get("documents", []),
        result.get("metadatas", []),
    ):
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "source_file": meta.get("source_file"),
        })
    return chunks


def reset_collection() -> None:
    """Delete all chunks — used in tests only. Wipes the Chroma collection."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        print("[store] Collection reset [OK]")
    except Exception:
        pass  # Collection didn't exist yet — that's fine
