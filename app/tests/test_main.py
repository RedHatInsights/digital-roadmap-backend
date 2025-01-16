def test_ping(api_prefix, client):
    response = client.get(f"{api_prefix}/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "pong"}
