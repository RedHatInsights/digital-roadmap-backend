def test_ping(client):
    response = client.get("/api/digital-roadmap/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "pong"}
