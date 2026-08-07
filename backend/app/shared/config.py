"""
config.py — Central configuration for AWS Bedrock, Qdrant, and MongoDB.

ENV modes:
  dev   → profile_name="aws" (if configured) or ambient AWS credentials
  local → endpoint_url=LOCALSTACK_ENDPOINT / local resources
  prod  → ambient IAM role (Lambda execution role / ECS task role)

Service clients:
  get_boto3_client() → Bedrock / S3 boto3 clients
  get_mongo_client() → MongoDB Atlas client
  get_qdrant_client()→ Qdrant Cloud or local client
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Search for .env in current dir, backend/, or parent dir
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path(".env"),
    Path("backend/.env"),
]
for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break

# ── Core settings ──────────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "dev")                     # dev | local | prod
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
LOCALSTACK_ENDPOINT = os.getenv("FLOCI_ENDPOINT", os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566"))

# ── Bedrock model IDs ──────────────────────────────────────────────────────────
TITAN_EMBED_MODEL_ID = os.getenv("TITAN_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
NOVA_LLM_MODEL_ID    = os.getenv("NOVA_LLM_MODEL_ID",    "amazon.nova-pro-v1:0")

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "cited_or_silent"
    qdrant_endpoint: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

# ── MongoDB Atlas ──────────────────────────────────────────────────────────────
MONGODB_URI = settings.mongodb_uri
MONGODB_DB  = settings.mongodb_db

# ── Qdrant Cloud ───────────────────────────────────────────────────────────────
QDRANT_ENDPOINT = settings.qdrant_endpoint
QDRANT_API_KEY  = settings.qdrant_api_key

# ── AWS S3 ─────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cited-or-silent-docs")


# ── boto3 client factory ────────────────────────────────────────────────────────
@lru_cache(maxsize=8)
def get_boto3_client(service_name: str):
    """
    Creates a boto3 client using the correct session/profile based on ENV.
    Gracefully falls back to default session if profile is missing.
    """
    import boto3
    from botocore.exceptions import ProfileNotFound

    kwargs = {"region_name": AWS_REGION}

    if ENV == "dev":
        try:
            session = boto3.Session(profile_name="aws")
        except ProfileNotFound:
            session = boto3.Session()
    elif ENV == "local":
        try:
            session = boto3.Session(profile_name="local")
        except ProfileNotFound:
            session = boto3.Session()
        kwargs["endpoint_url"] = LOCALSTACK_ENDPOINT
    else:
        # Dev and Prod modes will pick up AWS_ACCESS_KEY_ID or IAM roles automatically
        session = boto3.Session()

    return session.client(service_name, **kwargs)


@lru_cache(maxsize=1)
def get_mongo_client():
    """Lazy singleton MongoDB client."""
    from pymongo import MongoClient
    return MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)


def get_qdrant_client():
    """Returns a Qdrant client configured for cloud URL, local URL, or in-memory."""
    from qdrant_client import QdrantClient
    if QDRANT_ENDPOINT.startswith("http://") or QDRANT_ENDPOINT.startswith("https://"):
        if QDRANT_API_KEY:
            return QdrantClient(url=QDRANT_ENDPOINT, api_key=QDRANT_API_KEY, timeout=30)
        else:
            return QdrantClient(url=QDRANT_ENDPOINT, timeout=30)
    elif QDRANT_ENDPOINT == ":memory:":
        return QdrantClient(":memory:")
    else:
        return QdrantClient(path=QDRANT_ENDPOINT)


def get_s3_client():
    """Returns an S3 boto3 client."""
    return get_boto3_client("s3")
