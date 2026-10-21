import logging
import uuid

from datetime import date
from pathlib import Path

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.config import Settings
from roadmap.models import SystemInfo
from roadmap.v1.upcoming import get_upcoming_data_with_hosts
from roadmap.v1.upcoming import packages_by_system
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
    data = response.json()["data"]

    assert response.status_code == 200
    assert data[0]["name"] == "Add Node.js to RHEL9 AppStream THIS IS TEST DATA TEST FROM FIXTURES"
    assert data[0]["details"]["deployedDate"] == "2025-03-15"
    assert data[1]["details"]["deployedDate"] is None


def test_get_relevant_upcoming_changes_all(client, api_prefix):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
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
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
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


class _InventoryRows:
    def __init__(self, rows):
        self._rows = rows

    def yield_per(self, _batch_size):
        return self

    def mappings(self):
        return self

    async def __aiter__(self):
        for row in self._rows:
            yield row


async def test_packages_by_system_logs_omit_customer_data(caplog):
    """Inventory matching logs counts only, never the tenant id or host name."""
    org_id = "sensitive-org"
    display_name = "secret-host-name"
    rows = _InventoryRows(
        [
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "display_name": display_name,
                "packages": None,
            },
            {
                "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "display_name": display_name,
                "os_major": 9,
                "os_minor": 4,
                "packages": [],
            },
            {
                "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
                "display_name": display_name,
                "os_major": 9,
                "os_minor": 4,
                "packages": ["bash-5.1.8-9.el9.x86_64"],
            },
        ]
    )

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        result = await packages_by_system(org_id, rows)

    assert len(result) == 1
    assert org_id not in caplog.text
    assert display_name not in caplog.text
    assert "Getting packages by system" in caplog.text
    assert "Missing os_version: 1, packages: 1 while getting packages by system" in caplog.text


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
    assert any(item.details.deployedDate is not None for item in result), (
        "deployedDate should be returned in output details"
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
