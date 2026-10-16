from unittest.mock import AsyncMock

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.database import get_db


# These hosts are in tests/fixtures/inventory_db_response.json.gz.
# GroupOne (aec18a86-...) has the host with NGINX 1.22.
# The ungrouped host has Node.js 18 installed.
GROUP_ONE = "aec18a86-3593-11f0-8426-5e43c8b8aa2f"
GROUP_ONE_HOST = "a77a8458-3593-11f0-8426-5e43c8b8aa2f"
UNGROUPED_HOST = "44ea23ba-3661-11f0-b16d-5e43c8b8aa2f"
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
        f"{api_prefix}/relevant/lifecycle/app-streams/hosts",
        json={"host_ids": list(host_ids)},
        params={"related": related},
    )


def _installed(data):
    return [item for item in data if item["count"] > 0 and not item.get("related")]


def _stream_identity(item):
    """Fields that must match between the v1 endpoint and this host-scoped one."""
    return (
        item["name"],
        item["display_name"],
        item["os_major"],
        item["os_minor"],
        item["count"],
        item["related"],
        item["rolling"],
        item["support_status"],
        tuple(sorted(item["systems"])),
        tuple(sorted(detail["id"] for detail in item["systems_detail"])),
    )


def test_relevant_app_streams_for_all_hosts_matches_v1(api_prefix, client, read_json_fixture):
    """Every fixture host produces the same payload as the unscoped v1 endpoint."""
    _allow(client, set())
    host_ids = [host["id"] for host in read_json_fixture("inventory_db_response.json.gz")]

    scoped = _post(client, api_prefix, host_ids)
    unscoped = client.get(f"{api_prefix}/relevant/lifecycle/app-streams")

    assert scoped.status_code == 200, scoped.text
    assert unscoped.status_code == 200, unscoped.text

    scoped_body = scoped.json()
    unscoped_body = unscoped.json()
    data = scoped_body["data"]
    meta = scoped_body["meta"]

    assert meta["count"] == 29, "Incorrect number of items in response. Did the fixture data change?"
    assert meta["total"] == 226, "Incorrect number of hosts in response. Did the fixture data change?"
    assert meta == unscoped_body["meta"]

    display_names = {item["display_name"] for item in data}
    names = {item["name"] for item in data}
    assert display_names.issuperset(["PostgreSQL 15", "PostgreSQL 16", "Apache HTTPD 2.4", "MySQL 8.0"])
    assert names.issuperset(["Python 3.11", "python36", "MySQL 8.0", "nginx", "nodejs"])
    assert not any(item["rolling"] for item in data), "Rolling app streams should not be in the response"
    assert all(len(set(item["systems"])) == len(item["systems"]) for item in data)
    assert all(set(item["systems"]) == {detail["id"] for detail in item["systems_detail"]} for item in data)
    assert sorted(map(_stream_identity, data)) == sorted(map(_stream_identity, unscoped_body["data"]))


def test_relevant_app_streams_for_ungrouped_host(api_prefix, client):
    """
    The ungrouped host has Node.js 18 installed, plus related streams
    (Node.js 20, 22, 24, and so on) when related results are requested.
    """
    _allow(client, {None})

    result = _post(client, api_prefix, [UNGROUPED_HOST], related=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = [item for item in data if not item.get("related", False)]
    related = [item for item in data if item.get("related", False)]
    assert len(installed) == 1, f"Expected 1 installed stream, got {len(installed)}"
    assert installed[0]["display_name"] == "Node.js 18"
    assert installed[0]["count"] == 1
    assert set(installed[0]["systems"]) == {UNGROUPED_HOST}
    assert len(related) > 0, "Expected related streams for Node.js 18"
    related_names = {item["display_name"] for item in related}
    assert "Node.js 20" in related_names or "Node.js 22" in related_names
    assert all(item["count"] == 0 for item in related)
    assert all(item["systems"] == [] for item in related)


def test_relevant_app_streams_for_one_grouped_host(api_prefix, client):
    """A single requested host is the only inventory the response is built from.

    Group access is unrestricted, so the missing Node.js host is excluded by
    the id list rather than by RBAC.
    """
    _allow(client, set())

    result = _post(client, api_prefix, [GROUP_ONE_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert {item["display_name"] for item in installed} == {"NGINX 1.22"}
    assert all(set(item["systems"]) == {GROUP_ONE_HOST} for item in installed)
    assert "Node.js 18" not in {item["display_name"] for item in data}


def test_relevant_app_streams_for_ungrouped_and_grouped_hosts(api_prefix, client):
    """Both permitted hosts, matching the v1 combined group-permission result."""
    _allow(client, {None, GROUP_ONE})

    result = _post(client, api_prefix, [UNGROUPED_HOST, GROUP_ONE_HOST], related=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    installed_names = {item["display_name"] for item in installed}
    assert installed_names == {"Node.js 18", "NGINX 1.22"}
    related = [item for item in data if item.get("related", False)]
    assert len(related) > 0, "Expected related streams"
    assert "NGINX 1.14" not in installed_names
    systems = {system for item in installed for system in item["systems"]}
    assert systems == {UNGROUPED_HOST, GROUP_ONE_HOST}


def test_relevant_app_streams_omits_hosts_outside_allowed_groups(api_prefix, client):
    """A requested id the caller cannot read is left out of the inventory result."""
    _allow(client, {None})

    result = _post(client, api_prefix, [UNGROUPED_HOST, GROUP_ONE_HOST], related=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = [item for item in data if not item.get("related", False)]
    related = [item for item in data if item.get("related", False)]
    assert len(installed) == 1
    assert installed[0]["display_name"] == "Node.js 18"
    assert set(installed[0]["systems"]) == {UNGROUPED_HOST}
    assert "NGINX 1.22" not in {item["display_name"] for item in data}
    assert len(related) > 0
    related_names = {item["display_name"] for item in related}
    assert "Node.js 20" in related_names or "Node.js 22" in related_names


def test_relevant_app_streams_ignores_unknown_host_id(api_prefix, client):
    """An id that is not in inventory does not change the streams of a real host."""
    _allow(client, {None})

    result = _post(client, api_prefix, [UNGROUPED_HOST, UNKNOWN_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    assert installed[0]["display_name"] == "Node.js 18"
    assert set(installed[0]["systems"]) == {UNGROUPED_HOST}


def test_relevant_app_streams_duplicate_host_ids_count_once(api_prefix, client):
    """Repeating a host id does not count that host twice."""
    _allow(client, {None})

    result = _post(client, api_prefix, [UNGROUPED_HOST, UNGROUPED_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    installed = _installed(data)
    assert len(installed) == 1
    assert installed[0]["display_name"] == "Node.js 18"
    assert installed[0]["count"] == 1
    assert installed[0]["systems"] == [UNGROUPED_HOST]


def test_relevant_app_streams_for_hosts_no_rbac_access(api_prefix, client):
    async def get_allowed_host_groups_override():
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

    result = _post(client, api_prefix, [UNGROUPED_HOST])

    assert result.status_code == 403


def test_relevant_app_streams_for_hosts_database_error(api_prefix, client):
    _allow(client, set())
    session = AsyncMock()
    session.stream.side_effect = DBAPIError("Database connection timeout", None, None)
    client.app.dependency_overrides[get_db] = lambda: session

    result = _post(client, api_prefix, [UNGROUPED_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    session.stream.assert_awaited_once()


def test_relevant_app_streams_for_hosts_database_error_while_fetching(api_prefix, client):
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
                    "id": UNGROUPED_HOST,
                    "display_name": "ungrouped-host",
                    "os_major": 9,
                    "os_minor": 4,
                    "os_release": "9.4",
                    "dnf_modules": [],
                    "packages": [],
                    "products": [],
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

    result = _post(client, api_prefix, [UNGROUPED_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    assert "secret_inventory" not in result.text
    assert "sensitive-org" not in result.text
    session.stream.assert_awaited_once()


def test_relevant_app_streams_for_hosts_error_building_response(api_prefix, client, mocker):
    _allow(client, {None})
    mocker.patch("roadmap.v1.lifecycle.app_streams.RelevantAppStream", side_effect=ValueError("Raised intentionally"))

    result = _post(client, api_prefix, [UNGROUPED_HOST])

    assert result.status_code == 400
    assert result.json().get("detail") == "Raised intentionally"


def test_relevant_app_streams_for_hosts_accepts_empty_list(api_prefix, client):
    """An empty id list is valid and matches no hosts."""
    _allow(client, set())

    result = client.post(
        f"{api_prefix}/relevant/lifecycle/app-streams/hosts",
        json={"host_ids": []},
    )

    assert result.status_code == 200, result.text
    assert result.json() == {"meta": {"count": 0, "total": 0}, "data": []}
