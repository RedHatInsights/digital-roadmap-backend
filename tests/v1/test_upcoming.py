from pathlib import Path

from roadmap.common import decode_header
from roadmap.common import query_rbac
from roadmap.config import Settings


def test_get_upcoming_changes(client, api_prefix):
    response = client.get(f"{api_prefix}/upcoming-changes")
    data = response.json()["data"]

    assert response.status_code == 200
    assert data[0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA"
    assert not any("potentiallyAffectedSystems" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystems' field, that is in /relevent/upcoming-changes only"
    )
    assert not any("potentiallyAffectedSystemsCount" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystemsCount' field, that is in /relevent/upcoming-changes only"
    )


def test_get_upcoming_changes_with_env(client, api_prefix):
    def settings_override():
        return Settings(upcoming_json_path=Path(__file__).parent.parent.joinpath("fixtures").joinpath("upcoming.json"))

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    response = client.get(f"{api_prefix}/upcoming-changes")
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA TEST"


def test_get_relevant_upcoming_changes_all(client, api_prefix):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    response = client.get(f"{api_prefix}/relevant/upcoming-changes?all=true")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA"
    assert any(len(record["details"]["potentiallyAffectedSystems"]) == 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with no affected systems"
    )
    assert any(len(record["details"]["potentiallyAffectedSystems"]) > 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with affected systems"
    )


def test_get_relevant_upcoming_changes(client, api_prefix):
    async def query_rbac_override():
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    response = client.get(f"{api_prefix}/relevant/upcoming-changes")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA"
    assert not any(len(record["details"]["potentiallyAffectedSystems"]) == 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have no records with no affected systems"
    )
    assert any(len(record["details"]["potentiallyAffectedSystems"]) > 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with affected systems"
    )
