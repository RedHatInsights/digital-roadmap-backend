from datetime import date
from unittest.mock import AsyncMock

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.database import get_db
from roadmap.models import SupportStatus


# These hosts are in tests/fixtures/inventory_db_response.json.gz.
# GroupOne and GroupTwo each have one RHEL 9.4 host with product 241 (E4S).
# The ungrouped host is also RHEL 9.4 E4S.
GROUP_ONE = "aec18a86-3593-11f0-8426-5e43c8b8aa2f"
GROUP_ONE_HOST = "a77a8458-3593-11f0-8426-5e43c8b8aa2f"
GROUP_TWO_HOST = "e4a98798-3593-11f0-8426-5e43c8b8aa2f"
UNGROUPED_HOST = "44ea23ba-3661-11f0-b16d-5e43c8b8aa2f"
# RHEL 9.10 with product 204 (ELS). No host group.
ELS_HOST = "c687e3db-a681-4b27-afbf-7056cdc0f212"
# RHEL 9.4 mainline (product 479) and RHEL 9.4 EUS (product 70). No host group.
MAINLINE_9_4_HOST = "7b710ce5-d4f5-4ad1-888d-3bf70c8d9cca"
EUS_9_4_HOST = "1df9b88c-7838-4bbc-b173-995b816ae8ab"
# RHEL name, no major/minor and no os_release. The endpoint must skip it.
VERSIONLESS_HOST = "254748bc-c00a-4ca1-8b77-ed27d1df4685"
# No operating_system major/minor; os_release is 9.6, so the version comes from that.
OS_RELEASE_9_6_HOST = "52323f8c-f953-4b6c-882f-93e5270d92b2"
# RHEL 1.0 is not in the lifecycle table.
UNKNOWN_LIFECYCLE_HOST = "03499b8c-d56c-4581-b259-cbdebf19ae92"
UNKNOWN_HOST = "00000000-0000-4000-8000-000000000001"


def _allow(client, host_groups, org_id="1234"):
    """Skip the remote permission call and supply the groups the caller may read."""

    async def get_allowed_host_groups_override():
        return host_groups

    async def decode_header_override():
        return org_id

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override


def _post(client, api_prefix, host_ids, related=False):
    return client.post(
        f"{api_prefix}/relevant/lifecycle/rhel/hosts",
        json={"host_ids": list(host_ids)},
        params={"related": related},
    )


def _installed(data):
    return [item for item in data if item["count"] > 0 and not item["related"]]


def _version_identity(item):
    """Fields that must match between the unscoped endpoint and this host-scoped one."""
    return (
        item["name"],
        item["display_name"],
        item["major"],
        item["minor"],
        item["lifecycle_type"],
        item["count"],
        item["related"],
        item["start_date"],
        item["end_date"],
        item["support_status"],
        tuple(sorted(item["systems"])),
        tuple(sorted(detail["id"] for detail in item["systems_detail"])),
    )


def _still_supported_later_versions(major, minor, installed_keys):
    """Later minors of this major whose mainline end date is still in the future.

    Matches the related-version rule in the relevant RHEL aggregation: a minor
    of None sorts below every real minor, and an installed version is not
    repeated as a related row.
    """
    today = date.today()
    current_minor = minor if minor is not None else -1
    versions = set()
    for key, lifecycle in OS_LIFECYCLE_DATES.items():
        lifecycle_minor = lifecycle.minor if lifecycle.minor is not None else -1
        if lifecycle.major == major and lifecycle_minor > current_minor and lifecycle.end_date > today:
            if key not in installed_keys:
                versions.add((lifecycle.major, lifecycle.minor))
    return versions


def test_relevant_rhel_for_all_hosts_matches_unscoped(api_prefix, client, read_json_fixture):
    """Every fixture host produces the same payload as the unscoped relevant RHEL endpoint."""
    _allow(client, set())
    host_ids = [host["id"] for host in read_json_fixture("inventory_db_response.json.gz")]

    scoped = _post(client, api_prefix, host_ids)
    unscoped = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert scoped.status_code == 200, scoped.text
    assert unscoped.status_code == 200, unscoped.text

    scoped_body = scoped.json()
    unscoped_body = unscoped.json()
    data = scoped_body["data"]

    assert scoped_body["meta"] == unscoped_body["meta"]
    assert scoped_body["meta"]["count"] == len(data)
    assert scoped_body["meta"]["total"] == sum(item["count"] for item in data)
    assert all(item["count"] == len(item["systems"]) for item in data)
    assert all(set(item["systems"]) == {detail["id"] for detail in item["systems_detail"]} for item in data)
    assert sorted(map(_version_identity, data)) == sorted(map(_version_identity, unscoped_body["data"]))


def test_relevant_rhel_for_els_host(api_prefix, client):
    """A RHEL 9.10 ELS host uses the ELS end date, and nothing newer exists to relate."""
    _allow(client, set())

    result = _post(client, api_prefix, [ELS_HOST], related=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    related = [item for item in data if item["related"]]
    assert len(installed) == 1
    item = installed[0]
    assert (item["major"], item["minor"], item["lifecycle_type"]) == (9, 10, "ELS")
    assert item["display_name"] == "RHEL 9.10 ELS"
    assert item["end_date"] == OS_LIFECYCLE_DATES["9.10"].end_date_els.isoformat()
    assert item["start_date"] == OS_LIFECYCLE_DATES["9.10"].start_date.isoformat()
    assert item["count"] == 1
    assert set(item["systems"]) == {ELS_HOST}
    assert related == []
    assert _still_supported_later_versions(9, 10, {"9.10"}) == set()


def test_relevant_rhel_for_e4s_host_includes_later_supported_versions(api_prefix, client):
    """The GroupOne host is RHEL 9.4 for SAP. Related rows are later 9.x still in mainline support."""
    _allow(client, {GROUP_ONE})

    result = _post(client, api_prefix, [GROUP_ONE_HOST], related=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    related = [item for item in data if item["related"]]
    assert len(installed) == 1
    item = installed[0]
    assert (item["major"], item["minor"], item["lifecycle_type"]) == (9, 4, "E4S")
    assert item["display_name"] == "RHEL 9.4 for SAP"
    assert item["end_date"] == OS_LIFECYCLE_DATES["9.4"].end_date_e4s.isoformat()
    assert item["count"] == 1
    assert set(item["systems"]) == {GROUP_ONE_HOST}

    expected_related = _still_supported_later_versions(9, 4, {"9.4"})
    assert expected_related, "RHEL 9 should still have a supported minor after 9.4"
    assert {(row["major"], row["minor"]) for row in related} == expected_related
    assert all(row["lifecycle_type"] == "mainline" for row in related)
    assert all(row["count"] == 0 for row in related)
    assert all(row["systems"] == [] for row in related)
    assert all(
        row["end_date"] == OS_LIFECYCLE_DATES[f"{row['major']}.{row['minor']}"].end_date.isoformat() for row in related
    )


def test_relevant_rhel_keeps_same_version_on_separate_lifecycle_rows(api_prefix, client):
    """RHEL 9.4 mainline and RHEL 9.4 EUS are different rows with different end dates."""
    _allow(client, set())

    result = _post(client, api_prefix, [MAINLINE_9_4_HOST, EUS_9_4_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    by_lifecycle = {item["lifecycle_type"]: item for item in installed}
    assert set(by_lifecycle) == {"mainline", "EUS"}

    mainline = by_lifecycle["mainline"]
    eus = by_lifecycle["EUS"]
    assert (mainline["major"], mainline["minor"]) == (9, 4)
    assert (eus["major"], eus["minor"]) == (9, 4)
    assert mainline["end_date"] == OS_LIFECYCLE_DATES["9.4"].end_date.isoformat()
    assert eus["end_date"] == OS_LIFECYCLE_DATES["9.4"].end_date_eus.isoformat()
    assert mainline["display_name"] == "RHEL 9.4"
    assert eus["display_name"] == "RHEL 9.4 EUS"
    assert mainline["count"] == 1
    assert eus["count"] == 1
    assert set(mainline["systems"]) == {MAINLINE_9_4_HOST}
    assert set(eus["systems"]) == {EUS_9_4_HOST}
    assert result.json()["meta"]["total"] == 2
    assert result.json()["meta"]["count"] == 2


def test_relevant_rhel_merges_hosts_with_the_same_version_and_lifecycle(api_prefix, client):
    """Two RHEL 9.4 E4S hosts, in different groups, are one row with both system ids."""
    _allow(client, set())

    result = _post(client, api_prefix, [GROUP_ONE_HOST, GROUP_TWO_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    item = installed[0]
    assert (item["major"], item["minor"], item["lifecycle_type"]) == (9, 4, "E4S")
    assert item["count"] == 2
    assert set(item["systems"]) == {GROUP_ONE_HOST, GROUP_TWO_HOST}
    assert result.json()["meta"]["total"] == 2
    assert result.json()["meta"]["count"] == 1


def test_relevant_rhel_omits_hosts_outside_allowed_groups(api_prefix, client):
    """A requested id the caller cannot read is left out of the inventory result."""
    _allow(client, {GROUP_ONE})

    result = _post(client, api_prefix, [GROUP_ONE_HOST, UNGROUPED_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    assert (installed[0]["major"], installed[0]["minor"], installed[0]["lifecycle_type"]) == (9, 4, "E4S")
    assert installed[0]["count"] == 1
    assert set(installed[0]["systems"]) == {GROUP_ONE_HOST}


def test_relevant_rhel_ignores_unknown_host_id(api_prefix, client):
    """An id that is not in inventory does not change the lifecycle row of a real host."""
    _allow(client, set())

    result = _post(client, api_prefix, [ELS_HOST, UNKNOWN_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    assert (installed[0]["major"], installed[0]["minor"]) == (9, 10)
    assert installed[0]["count"] == 1
    assert set(installed[0]["systems"]) == {ELS_HOST}


def test_relevant_rhel_duplicate_host_ids_count_once(api_prefix, client):
    """Repeating a host id does not count that host twice."""
    _allow(client, set())

    result = _post(client, api_prefix, [ELS_HOST, ELS_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    assert installed[0]["count"] == 1
    assert installed[0]["systems"] == [ELS_HOST]


def test_relevant_rhel_skips_versionless_host_and_uses_os_release_fallback(api_prefix, client):
    """A host with no version is omitted. A host whose version is only in os_release is RHEL 9.6."""
    _allow(client, set())

    result = _post(client, api_prefix, [VERSIONLESS_HOST, OS_RELEASE_9_6_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    item = installed[0]
    assert (item["name"], item["major"], item["minor"], item["lifecycle_type"]) == ("RHEL", 9, 6, "mainline")
    assert item["end_date"] == OS_LIFECYCLE_DATES["9.6"].end_date.isoformat()
    assert item["count"] == 1
    assert set(item["systems"]) == {OS_RELEASE_9_6_HOST}
    assert VERSIONLESS_HOST not in item["systems"]


def test_relevant_rhel_unknown_lifecycle_dates(api_prefix, client):
    """RHEL 1.0 has no lifecycle record. The host is still returned, with unknown dates."""
    _allow(client, set())

    result = _post(client, api_prefix, [UNKNOWN_LIFECYCLE_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    assert len(data) == 1
    item = data[0]
    assert (item["name"], item["major"], item["minor"]) == ("RHEL", 1, 0)
    assert item["start_date"] == SupportStatus.unknown
    assert item["end_date"] == SupportStatus.unknown
    assert item["count"] == 1
    assert set(item["systems"]) == {UNKNOWN_LIFECYCLE_HOST}


def test_relevant_rhel_for_hosts_no_rbac_access(api_prefix, client):
    async def get_allowed_host_groups_override():
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

    result = _post(client, api_prefix, [ELS_HOST])

    assert result.status_code == 403


def test_relevant_rhel_for_hosts_database_error(api_prefix, client):
    _allow(client, set())
    session = AsyncMock()
    session.stream.side_effect = DBAPIError("Database connection timeout", None, None)
    client.app.dependency_overrides[get_db] = lambda: session

    result = _post(client, api_prefix, [ELS_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    session.stream.assert_awaited_once()


def test_relevant_rhel_for_hosts_database_error_while_fetching(api_prefix, client):
    """A failure while reading rows, after stream() has returned, is still a safe 500."""
    _allow(client, set())

    class _Rows:
        def __init__(self):
            self._sent = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._sent:
                self._sent = True
                return {
                    "id": ELS_HOST,
                    "display_name": "els-host",
                    "os_name": "RHEL",
                    "os_major": 9,
                    "os_minor": 10,
                    "os_release": "9.10",
                    "products": [{"id": "204"}],
                }
            raise DBAPIError("SELECT secret_inventory WHERE org_id = :org_id", {"org_id": "sensitive-org"}, None)

    class _Result:
        def yield_per(self, batch_size):
            return self

        def mappings(self):
            return _Rows()

    session = AsyncMock()
    session.stream = AsyncMock(return_value=_Result())
    client.app.dependency_overrides[get_db] = lambda: session

    result = _post(client, api_prefix, [ELS_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    assert "secret_inventory" not in result.text
    assert "sensitive-org" not in result.text
    session.stream.assert_awaited_once()


def test_relevant_rhel_for_hosts_accepts_empty_list(api_prefix, client):
    """An empty id list is valid and matches no hosts."""
    _allow(client, set())

    result = client.post(
        f"{api_prefix}/relevant/lifecycle/rhel/hosts",
        json={"host_ids": []},
    )

    assert result.status_code == 200, result.text
    assert result.json() == {"meta": {"count": 0, "total": 0}, "data": []}
