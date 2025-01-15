from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upcoming_mock_endpoint():
    response = client.get("/api/digital-roadmap/v1/upcoming-changes")
    assert response.status_code == 200
