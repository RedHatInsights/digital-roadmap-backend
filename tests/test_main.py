def test_ping(client):
    response = client.get("/api/digital-roadmap/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "pong"}


def test_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"digital_roadmap_http_request" in response.read()
