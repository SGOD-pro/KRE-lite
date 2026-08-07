"""
shared/config.py — minimal Phase 0 config.

Phase 0 needs nothing from AWS / Qdrant / MongoDB.
All service-specific config will be added in Phase 1 when those
dependencies are added to requirements.txt.

ENV var   : value   | meaning
----------|---------|-------------------------------------------------
ENV       | local   | running via docker-compose locally (default)
ENV       | prod    | (future) deployed
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present (no-op if missing)

# ── Core ─────────────────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "local")

# ── API port (informational — uvicorn reads this from CMD, not here) ─────────
API_PORT = int(os.getenv("API_PORT", "8000"))

# ── Phase 1+ config placeholders ─────────────────────────────────────────────
# These env vars are documented here so the .env.example stays in sync,
# but the actual client factories are added when Phase 1 deps are installed.
#
# LLM_API_KEY      = os.getenv("LLM_API_KEY", "")        # NVIDIA Build / OpenRouter
# LLM_BASE_URL     = os.getenv("LLM_BASE_URL", "")
# LLM_MODEL        = os.getenv("LLM_MODEL", "")
# CHROMA_PATH      = os.getenv("CHROMA_PATH", "./chroma_db")
# BM25_CACHE_PATH  = os.getenv("BM25_CACHE_PATH", "./bm25_index")
