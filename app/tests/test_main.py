def test_ping(client, api_prefix):
    response = client.get(f"{api_prefix}/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "pong"}
