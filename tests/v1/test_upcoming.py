from pathlib import Path

import roadmap.v1.upcoming


def test_get_upcoming_changes(client, api_prefix):
    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "New CLI experience for RHEL Image Builder"


def test_get_upcoming_changes_with_env(client, api_prefix, monkeypatch):
    monkeypatch.setenv(
        "ROADMAP_UPCOMING_JSON_PATH",
        str(Path(__file__).parent.parent.joinpath("fixtures").joinpath("upcoming.json")),
    )
    roadmap.v1.upcoming.get_upcoming_data.cache_clear()
    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "New CLI experience for RHEL Image Builder TEST"
