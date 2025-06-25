from pathlib import Path

from roadmap.common import decode_header
from roadmap.common import query_rbac
from roadmap.config import Settings
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.upcoming import get_upcoming_data_with_hosts


def test_get_upcoming_changes(client, api_prefix):
    response = client.get(f"{api_prefix}/upcoming-changes")
    data = response.json()["data"]

    assert response.status_code == 200
    assert "Add Node.js to RHEL9 AppStream THIS IS TEST DATA" in [n["name"] for n in data]
    assert not any("potentiallyAffectedSystems" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystems' field, that is in /relevent/upcoming-changes only"
    )
    assert not any("potentiallyAffectedSystemsCount" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystemsCount' field, that is in /relevent/upcoming-changes only"
    )


def test_get_upcoming_changes_with_env(client, api_prefix):
    def settings_override():
        return Settings(upcoming_json_path=Path(__file__).parents[1] / "fixtures" / "upcoming.json")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    response = client.get(f"{api_prefix}/upcoming-changes")

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA TEST FROM FIXTURES"


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
    data = response.json()["data"]

    assert response.status_code == 200
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
    data = response.json()["data"]

    assert response.status_code == 200
    assert "Add Node.js to RHEL9 AppStream THIS IS TEST DATA" in [n["name"] for n in data]
    assert not any(len(record["details"]["potentiallyAffectedSystems"]) == 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have no records with no affected systems"
    )
    assert any(len(record["details"]["potentiallyAffectedSystems"]) > 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with affected systems"
    )


def test_get_upcoming_data_with_hosts():
    """Given only AppStreamKey objects with os_major defined (no values of None),
    ensure the function returns as expected.
    """
    versions = range(9, 11)
    systems_by_app_stream = {
        AppStreamKey(
            name="Yo",
            app_stream_entity=AppStreamEntity(
                name="Yo",
                application_stream_name="Yo",
                stream="2.0",
                os_major=version,
                impl=AppStreamImplementation.package,
            ),
        ): set()
        for version in versions
    }
    settings = Settings.create()
    result = get_upcoming_data_with_hosts(systems_by_app_stream, settings)
    releases = [n.release for n in result]

    assert len(result) >= 1
    assert not any(release.startswith("8") for release in releases), "Something went wrong"
