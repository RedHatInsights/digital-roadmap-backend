from pathlib import Path

from roadmap.config import Settings


def test_get_upcoming_changes(client, api_prefix):
    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "New CLI experience for RHEL Image Builder"


def test_get_upcoming_changes_with_env(client, api_prefix):
    def settings_override():
        return Settings(
            upcoming_json_path=str(Path(__file__).parent.parent.joinpath("fixtures").joinpath("upcoming.json"))
        )

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "New CLI experience for RHEL Image Builder TEST"
