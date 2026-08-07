"""
embed_service.py — AWS Bedrock Titan Text Embeddings v2.

Uses boto3 to invoke Amazon Bedrock Runtime.
Model: amazon.titan-embed-text-v2:0 (1024 dimensions).

Features:
- Sequential embedding with retry and exponential backoff on throttling.
- embed_texts: Embeds a list of document chunks.
- embed_query: Embeds a single search query.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import List

from app.shared.config import TITAN_EMBED_MODEL_ID, get_boto3_client

EMBEDDING_DIM = 1024
BEDROCK_RETRY_ATTEMPTS = 5


@lru_cache(maxsize=1)
def _get_bedrock_client():
    """Lazy-init boto3 Bedrock Runtime client."""
    return get_boto3_client("bedrock-runtime")


def _embed_single(text: str) -> List[float]:
    """
    Call Bedrock Titan Embed v2 for a single text string.
    Retries on ThrottlingException or transient network errors.
    """
    if not text.strip():
        # Bedrock Titan requires non-empty text
        text = " "

    client = _get_bedrock_client()
    body = json.dumps({"inputText": text, "dimensions": EMBEDDING_DIM})

    for attempt in range(BEDROCK_RETRY_ATTEMPTS):
        try:
            response = client.invoke_model(
                modelId=TITAN_EMBED_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            return result["embedding"]
        except Exception as exc:
            err_str = str(exc)
            if ("ThrottlingException" in err_str or "TooManyRequests" in err_str) and attempt < BEDROCK_RETRY_ATTEMPTS - 1:
                wait_time = (2 ** attempt) * 0.5
                print(f"[embed] Throttled on attempt {attempt + 1}, retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            if attempt < BEDROCK_RETRY_ATTEMPTS - 1:
                time.sleep(0.3)
                continue
            raise RuntimeError(f"Bedrock Titan embedding failed after {BEDROCK_RETRY_ATTEMPTS} attempts: {exc}") from exc

    raise RuntimeError("Bedrock Titan embedding failed.")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of chunk texts via AWS Bedrock Titan.
    Returns a list of 1024-dimensional vectors.
    """
    if not texts:
        return []
    
    results = []
    total = len(texts)
    for i, text in enumerate(texts):
        if total > 5 and (i + 1) % 10 == 0:
            print(f"[embed] Embedding chunk {i + 1}/{total}...")
        emb = _embed_single(text)
        results.append(emb)
    return results


def embed_query(query: str) -> List[float]:
    """
    Embed a search query string via Bedrock Titan.
    """
    if not query.strip():
        raise ValueError("embed_query: query must not be empty")
    return _embed_single(query)
