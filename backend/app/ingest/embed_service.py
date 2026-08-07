"""
embed_service.py — BGE-small-en-v1.5 embeddings via sentence-transformers.

ARCHITECTURE.md: "BGE-small-en-v1.5 (ONNX, local, CPU) — zero API cost,
zero network hop."

We use sentence-transformers with the BGE-small-en-v1.5 model. The library
downloads the model weights on first use and caches them locally. No external
API call is made during inference — it runs entirely on CPU via PyTorch/ONNX.

NOTE on ONNX: sentence-transformers can use the ONNX backend via
optimum[onnxruntime]. For simplicity in the 48h window we use the standard
PyTorch backend (same model, same weights) which sentence-transformers ships
by default. The ONNX runtime can be swapped in later without changing the API.

Vector dimension: 384 (BGE-small-en-v1.5)
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

# Lazy import — model loads on first call, not at module import time.
# This keeps startup fast and allows tests to mock without loading the model.


@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load and cache the BGE-small-en-v1.5 SentenceTransformer model."""
    from sentence_transformers import SentenceTransformer
    print("[embed] Loading BGE-small-en-v1.5 model (first call — cached thereafter)...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    print("[embed] Model loaded [OK]")
    return model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of passage strings.
    Returns one 384-dim vector per input.
    Runs locally on CPU — no external API call.
    """
    if not texts:
        return []
    model = _get_model()
    # BGE models use a passage prefix for indexing passages
    prefixed = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    """
    Embed a single query string.
    Returns a 384-dim vector. No prefix needed for queries with BGE models.
    """
    if not query.strip():
        raise ValueError("embed_query: query must not be empty")
    model = _get_model()
    embedding = model.encode(query, normalize_embeddings=True, show_progress_bar=False)
    return embedding.tolist()


# Dimension constant — used by store.py to create the Chroma collection
EMBEDDING_DIM = 384
