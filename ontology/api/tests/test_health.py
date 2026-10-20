from fastapi.testclient import TestClient

from app.main import app


def test_health_is_available_without_database_access():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
