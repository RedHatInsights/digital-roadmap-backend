def test_get_release_notes(client, api_prefix):
    params = {"major": 9, "minor": 5}
    response = client.get(f"{api_prefix}/release-notes", params=params)
    data = response.json()

    assert response.status_code == 200
    assert len(data) > 0
