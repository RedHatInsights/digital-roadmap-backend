import importlib

from pathlib import Path

import roadmap.v1.upcoming


def test_get_upcoming_changes(client, api_prefix, monkeypatch):
    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.content.startswith(b'[{"name":"Node.js 22 included in RHEL 9 Application Streams","type":')

    monkeypatch.setenv(
        "ROADMAP_UPCOMING_JSON_PATH",
        str(Path(__file__).parent.parent.joinpath("fixtures").resolve().joinpath("upcoming.json")),
    )
    importlib.reload(roadmap.v1.upcoming)
    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.content.startswith(b'[{"name":"Node.js 22 included in RHEL 9 Application Streams TEST","type":')
