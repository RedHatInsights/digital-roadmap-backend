from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import httpx
import pytest

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from roadmap.common import _build_host_uuids_query
from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_accessible_host_uuids
from roadmap.config import Settings


# These hosts are in tests/fixtures/inventory_db_response.json.gz.
# GroupOne (aec18a86-...) has one host. GroupTwo is a different host.
# The ungrouped group is the host whose groups[].ungrouped is true.
GROUP_ONE = "aec18a86-3593-11f0-8426-5e43c8b8aa2f"
GROUP_ONE_HOST = "a77a8458-3593-11f0-8426-5e43c8b8aa2f"
GROUP_TWO_HOST = "e4a98798-3593-11f0-8426-5e43c8b8aa2f"
UNGROUPED_HOST = "44ea23ba-3661-11f0-b16d-5e43c8b8aa2f"
# Present in RBAC-style tests elsewhere, but not assigned to any fixture host.
UNKNOWN_GROUP = "ebeaf62a-9713-4dad-8d63-32b51cadbda3"


def _allow(client, host_groups, org_id="1234"):
    """Skip the remote permission call and supply the groups the caller may read."""

    async def get_allowed_host_groups_override():
        return host_groups

    async def decode_header_override():
        return org_id

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override


def _fixture_host_ids(read_json_fixture) -> set[str]:
    """Every host id the loader inserts for org 1234."""
    hosts = read_json_fixture("inventory_db_response.json.gz")
    return {host["id"] for host in hosts}


def test_build_host_uuids_query_is_id_only():
    """The UUID query must not read profile, package, or module columns."""
    query = _build_host_uuids_query()

    assert "SELECT h.id" in query
    assert "ORDER BY h.id" in query
    assert "system_profiles" not in query
    assert "installed_packages" not in query
    assert "dnf_modules" not in query
    assert "ungrouped" not in query
    assert ":host_groups" not in query


@pytest.mark.parametrize(
    ("host_groups", "expected"),
    (
        ({GROUP_ONE}, (":host_groups",)),
        ({None}, ("ungrouped",)),
        ({None, GROUP_ONE}, ("ungrouped", ":host_groups")),
    ),
)
def test_build_host_uuids_query_host_group_filters(host_groups, expected):
    """Group filtering uses the same fragments as the full inventory query."""
    query = _build_host_uuids_query(host_groups)

    for item in expected:
        assert item in query
    assert "installed_packages" not in query


def test_accessible_host_uuids_unrestricted(v2_prefix, client, read_json_fixture):
    """An empty group set is unrestricted access: every host in the org."""
    _allow(client, set())

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")
    body = result.json()
    uuids = body["accessible_host_uuids"]

    assert result.status_code == 200
    assert set(body) == {"accessible_host_uuids"}
    assert set(uuids) == _fixture_host_ids(read_json_fixture)
    assert len(uuids) == len(set(uuids)), "Found duplicate host UUIDs"


def test_accessible_host_uuids_no_rbac_access(v2_prefix, client):
    async def get_allowed_host_groups_override():
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")

    assert result.status_code == 403


def test_accessible_host_uuids_rbac_error(v2_prefix, client, mocker):
    """A failing RBAC call is returned to the client. Dev mode is off, so the check runs."""

    def settings_override():
        return Settings(rbac_hostname="example.com")

    error_response = httpx.Response(400)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Raised intentionally", request=httpx.Request("GET", "http://example.com"), response=error_response
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("roadmap.common.httpx.AsyncClient", return_value=mock_client)

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")

    assert result.status_code == 400
    mock_client.get.assert_awaited()


def test_accessible_host_uuids_dev_mode_skips_rbac(v2_prefix, client, mocker, read_json_fixture):
    """Dev mode does not call RBAC and still lists the fixture org's hosts."""

    def settings_override():
        return Settings(dev=True, rbac_hostname="example.com")

    mocker.patch("roadmap.common.httpx.AsyncClient", side_effect=AssertionError("RBAC should not be called"))

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[Settings.create] = settings_override

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")
    uuids = result.json()["accessible_host_uuids"]

    assert result.status_code == 200
    assert set(uuids) == _fixture_host_ids(read_json_fixture)


def test_accessible_host_uuids_single_group(v2_prefix, client):
    """A caller limited to one group receives only the hosts in that group."""
    _allow(client, {GROUP_ONE})

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")
    uuids = set(result.json()["accessible_host_uuids"])

    assert result.status_code == 200
    assert uuids == {GROUP_ONE_HOST}
    assert GROUP_TWO_HOST not in uuids
    assert UNGROUPED_HOST not in uuids


def test_accessible_host_uuids_unknown_group(v2_prefix, client):
    """A group id that no fixture host belongs to yields an empty list."""
    _allow(client, {UNKNOWN_GROUP})

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")

    assert result.status_code == 200
    assert result.json()["accessible_host_uuids"] == []


def test_accessible_host_uuids_ungrouped(v2_prefix, client):
    """
    Given a group with value None, which means "ungrouped", assert that only
    the host which belongs to the "ungrouped" group is returned.
    """
    _allow(client, {None})

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")
    uuids = set(result.json()["accessible_host_uuids"])

    assert result.status_code == 200
    assert uuids == {UNGROUPED_HOST}


def test_accessible_host_uuids_ungrouped_and_grouped(v2_prefix, client):
    """None means 'ungrouped', and is combined with a real group id."""
    _allow(client, {None, GROUP_ONE})

    result = client.get(f"{v2_prefix}/lifecycle/host_uuids")
    uuids = set(result.json()["accessible_host_uuids"])

    assert result.status_code == 200
    assert uuids == {UNGROUPED_HOST, GROUP_ONE_HOST}
    assert GROUP_TWO_HOST not in uuids


async def test_query_accessible_host_uuids_database_error():
    """A database failure while listing ids becomes a 500."""
    session = AsyncMock()
    session.stream = AsyncMock(side_effect=DBAPIError("Database connection timeout", None, None))

    with pytest.raises(HTTPException, match="Error querying host inventory") as exc_info:
        await anext(
            query_accessible_host_uuids(
                org_id="1234",
                session=session,
                settings=Settings(dev=False),
                host_groups=set(),
            )
        )

    assert exc_info.value.status_code == 500
