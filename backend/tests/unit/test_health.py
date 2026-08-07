"""
tests/unit/test_health.py — Phase 0 exit criterion.

Verifies that GET /health returns HTTP 200 with {"status": "ok"}.
This test must pass from commit one and never regress.

PHASES.md Phase 0 exit criteria:
  ✓ `docker-compose up` starts the FastAPI app, `/health` returns 200.
  ✓ CI pipeline green on a trivial commit.
"""
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /health must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status():
    """GET /health body must be {\"status\": \"ok\"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_ingest_stub_returns_501():
    """POST /ingest is a Phase 1 stub — must return 501 Not Implemented."""
    response = client.post("/ingest")
    assert response.status_code == 501


def test_query_stub_returns_501():
    """POST /query is a Phase 2 stub — must return 501 Not Implemented."""
    response = client.post("/query")
    assert response.status_code == 501
