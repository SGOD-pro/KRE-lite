"""
config.py — central config, loaded from .env.

Three ENV modes:
  dev   → profile_name="aws", real AWS (Bedrock + RDS + ElastiCache)
  local → profile_name="local", endpoint_url=http://localhost:4566 (Floci)
          RDS and Redis connect to localhost directly (psycopg2 / redis-py
          don't go through boto3, they use the TCP host/port directly)
  prod  → no profile, no endpoint override — boto3 picks up IAM role
          (ECS task role / EC2 instance profile / Lambda execution role)

All service clients are created via get_boto3_kwargs() / get_boto3_kwargs_local()
so callers never hard-code credentials.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env (no-op if not found)

# ── Core settings ──────────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "dev")                     # dev | local | prod
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
LOCALSTACK_ENDPOINT = os.getenv("FLOCI_ENDPOINT", "http://localhost:4566")

# ── Bedrock model IDs ──────────────────────────────────────────────────────────
TITAN_EMBED_MODEL_ID = os.getenv("TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
NOVA_LLM_MODEL_ID    = os.getenv("NOVA_LLM_MODEL_ID",    "amazon.nova-pro-v1:0")

# ── MongoDB Atlas ──────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB  = os.getenv("MONGODB_DB", "cited_or_silent")

# ── Qdrant Cloud ───────────────────────────────────────────────────────────────
QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT", "http://localhost:6333")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY", "")

# ── AWS S3 ─────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cited-or-silent-docs")


# ── boto3 client factory ────────────────────────────────────────────────────────
@lru_cache(maxsize=8)
def get_boto3_client(service_name: str):
    """
    Creates a boto3 client using the correct session/profile based on ENV.
    """
    import boto3
    kwargs = {"region_name": AWS_REGION}

    if ENV == "local":
        session = boto3.Session(profile_name="local")
        kwargs["endpoint_url"] = LOCALSTACK_ENDPOINT
    else:
        # Dev and Prod modes will pick up AWS_ACCESS_KEY_ID or IAM roles automatically
        session = boto3.Session()

    return session.client(service_name, **kwargs)


@lru_cache(maxsize=1)
def get_mongo_client():
    """Lazy singleton MongoDB client."""
    from pymongo import MongoClient
    return MongoClient(MONGODB_URI)


def get_qdrant_client():
    """Returns a new Qdrant client to avoid idle connection drop on long Bedrock sleeps."""
    from qdrant_client import QdrantClient
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_ENDPOINT, api_key=QDRANT_API_KEY, timeout=30)
    else:
        return QdrantClient(url=QDRANT_ENDPOINT, timeout=30)


def get_s3_client():
    """Returns an S3 boto3 client (not cached — S3 client is thread-safe)."""
    return get_boto3_client("s3")
