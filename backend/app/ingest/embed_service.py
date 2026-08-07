"""
embed_service.py — AWS Bedrock Titan Text Embeddings v2.

Uses boto3 to call Bedrock Runtime.
Region and credentials are pulled from config.py (dev uses profile_name="aws",
prod uses the ambient IAM role — no profile).

ARCHITECTURE.md: "Amazon Bedrock Titan Embeddings for high-dimensional semantic search."

RATE LIMIT NOTE: Bedrock Titan v2 has strict throughput limits.
We MUST sleep 1.4s after every embedding call to avoid ThrottlingException.
Embeddings are run SEQUENTIALLY (NOT in parallel) for this reason.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import List

import boto3

from app.shared.config import TITAN_EMBED_MODEL_ID, get_boto3_client

# Mandatory inter-embedding delay to respect Bedrock rate limits
BEDROCK_SLEEP_SECONDS = 1.4


@lru_cache(maxsize=1)
def _get_bedrock_client():
    """Lazy-init boto3 Bedrock Runtime client, cached per process."""
    return get_boto3_client("bedrock-runtime")


def _embed_single(text: str) -> List[float]:
    """
    Call Bedrock Titan Embed v2 for a single text string.
    Retries on ThrottlingException with backoff.
    Enforces BEDROCK_SLEEP_SECONDS after a successful call.
    """
    client = _get_bedrock_client()
    body = json.dumps({"inputText": text})

    for attempt in range(6):
        try:
            response = client.invoke_model(
                modelId=TITAN_EMBED_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            embedding = result["embedding"]
            # Mandatory sleep AFTER each successful embedding to respect rate limits
            time.sleep(BEDROCK_SLEEP_SECONDS)
            return embedding
        except Exception as exc:
            if "ThrottlingException" in str(exc) and attempt < 5:
                wait = 2.0 * (attempt + 1)
                print(f"[embed] ThrottlingException on attempt {attempt + 1}, sleeping {wait}s")
                time.sleep(wait)
                continue
            raise exc
    raise RuntimeError("Failed to embed text after 6 retries.")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of passage strings SEQUENTIALLY with 1.4s delay between each.
    Returns one vector per input.
    NOTE: intentionally NOT parallelised — Bedrock rate limit enforcement.
    """
    if not texts:
        return []
    results = []
    total = len(texts)
    for i, text in enumerate(texts):
        print(f"[embed] Embedding chunk {i + 1}/{total}...")
        results.append(_embed_single(text))
    return results


def embed_query(query: str) -> List[float]:
    """Embed a single query string via Bedrock Titan (no sleep — query path)."""
    client = _get_bedrock_client()
    body = json.dumps({"inputText": query})
    for attempt in range(6):
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
            if "ThrottlingException" in str(exc) and attempt < 5:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise exc
    raise RuntimeError("Failed to embed query after retries.")
