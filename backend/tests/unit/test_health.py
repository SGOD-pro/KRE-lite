"""
tests/unit/test_health.py — Basic API endpoint liveness tests.

Verifies GET /health returns HTTP 200 with {"status": "ok"}.
Verifies POST /query returns HTTP 400 for empty question.
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


def test_query_empty_question_returns_400():
    """POST /query with empty question must return 400."""
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 400
