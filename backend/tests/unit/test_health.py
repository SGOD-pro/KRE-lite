"""
tests/unit/test_health.py — Phase 0 exit criterion (must never regress).

Verifies GET /health returns HTTP 200 with {"status": "ok"}.

Phase 1 update: /ingest is now implemented (returns 200, not 501).
  The 501 test has been removed. /ingest is tested in test_ingestion.py.
  /query remains a 501 stub until Phase 2.
"""
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /health must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status():
    """GET /health body must be {"status": "ok"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_query_stub_returns_501():
    """POST /query is a Phase 2 stub — must return 501 Not Implemented."""
    response = client.post("/query")
    assert response.status_code == 501
