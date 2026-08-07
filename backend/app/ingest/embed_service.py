"""
embed_service.py — AWS Bedrock Titan Text Embeddings v2.

Uses boto3 to call Bedrock Runtime.
Region and credentials are pulled from config.py (dev uses profile_name="aws",
prod uses the ambient IAM role — no profile).

ARCHITECTURE.md: "Amazon Bedrock Titan Embeddings for high-dimensional semantic search."
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import List

import boto3

from app.shared.config import TITAN_EMBED_MODEL_ID, get_boto3_client


@lru_cache(maxsize=1)
def _get_bedrock_client():
    """Lazy-init boto3 Bedrock Runtime client, cached per process."""
    return get_boto3_client("bedrock-runtime")


def _embed_single(text: str) -> List[float]:
    """Call Bedrock Titan Embed v2 for a single text string."""
    client = _get_bedrock_client()
    body = json.dumps({"inputText": text})
    response = client.invoke_model(
        modelId=TITAN_EMBED_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of passage strings. Returns one vector per input."""
    return [_embed_single(t) for t in texts]


def embed_query(query: str) -> List[float]:
    """Embed a single query string via Bedrock Titan."""
    return _embed_single(query)
