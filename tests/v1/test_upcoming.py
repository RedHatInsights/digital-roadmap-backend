import uuid

from datetime import date
from pathlib import Path

from roadmap.common import decode_header
from roadmap.common import query_rbac
from roadmap.config import Settings
from roadmap.models import SystemInfo
from roadmap.v1.upcoming import get_upcoming_data_with_hosts
from roadmap.v1.upcoming import UpcomingOutputDetails


def test_get_upcoming_changes(client, api_prefix):
    response = client.get(f"{api_prefix}/upcoming-changes")
    data = response.json()["data"]
    package_results = [(result["package"], result["packages"]) for result in data]

    assert response.status_code == 200
    assert "Add Node.js to RHEL9 AppStream THIS IS TEST DATA" in [n["name"] for n in data]
    assert not any("potentiallyAffectedSystems" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystems' field, that is in /relevent/upcoming-changes only"
    )
    assert not any("potentiallyAffectedSystemsCount" in d["details"] for d in data), (
        "/upcoming-changes should have no 'potentiallyAffectedSystemsCount' field, that is in /relevent/upcoming-changes only"
    )
    assert all(package == sorted(packages)[0] for package, packages in package_results), (
        "Package does not match the first item in packages"
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
    releases = []
    for record in data:
        if affected_systems := record["details"]["potentiallyAffectedSystemsDetail"]:
            major_release = {int(record["release"].split(".", 1)[0])}
            os_majors = {system["os_major"] for system in affected_systems}
            releases.append((major_release, os_majors))

    assert response.status_code == 200
    assert any(len(record["details"]["potentiallyAffectedSystems"]) == 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with zero affected systems"
    )
    assert any(len(record["details"]["potentiallyAffectedSystems"]) > 0 for record in data), (
        "/relevant/upcoming-changes?all=true should have records with affected systems"
    )
    assert all(major_release == os_majors for major_release, os_majors in releases), (
        "Affected system versions do not match release version. Look at 'releases'."
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
    releases = []
    for record in data:
        if affected_systems := record["details"]["potentiallyAffectedSystemsDetail"]:
            major_release = {int(record["release"].split(".", 1)[0])}
            os_majors = {system["os_major"] for system in affected_systems}
            releases.append((major_release, os_majors))

    assert response.status_code == 200
    assert "Add Node.js to RHEL10 AppStream THIS IS TEST DATA" in [n["name"] for n in data]
    assert not any(len(record["details"]["potentiallyAffectedSystems"]) == 0 for record in data), (
        "/relevant/upcoming-changes should have no records with zero affected systems"
    )
    assert any(len(record["details"]["potentiallyAffectedSystems"]) > 0 for record in data), (
        "/relevant/upcoming-changes should have records with affected systems"
    )
    assert all(major_release == os_majors for major_release, os_majors in releases), (
        "Affected system versions do not match release version. Look at 'releases'."
    )


def test_get_upcoming_data_with_hosts():
    """Given only RHEL 9 and 10 hosts, ensure that upcoming items relevant
    to RHEL 8 are matched.
    """
    systems = [SystemInfo(id=uuid.uuid4(), display_name=f"RHEL {n}", os_major=n, os_minor=None) for n in range(9, 11)]
    packages_by_system = {system: {"nodejs"} for system in systems}
    settings = Settings.create()
    result = get_upcoming_data_with_hosts(packages_by_system, settings)
    releases = [n.release for n in result]

    assert len(result) >= 1
    assert not any(release.startswith("8") for release in releases), (
        "An upcoming item for RHEL 8 was incorrectly returned in the results"
    )


def test_upcoming_populate_systems_from_systems_detail(make_systems):
    """Check that the systems attribute is set properly by field validation."""

    count = 2
    system_ids, systems_detail = make_systems(count)

    upcoming = UpcomingOutputDetails(
        architecture=None,
        detailFormat=0,
        summary="Summary",
        trainingTicket="Ticket",
        dateAdded=date.today(),
        lastModified="2025-01-01",
        potentiallyAffectedSystemsCount=count,
        potentiallyAffectedSystemsDetail=systems_detail,
    )

    assert upcoming.potentiallyAffectedSystems == system_ids
