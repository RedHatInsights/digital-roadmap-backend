from unittest.mock import AsyncMock

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.v1.upcoming import read_upcoming_file


# These hosts are in tests/fixtures/inventory_db_response.json.gz.
# GroupOne's host has a RHEL version and no installed packages.
GROUP_ONE = "aec18a86-3593-11f0-8426-5e43c8b8aa2f"
NO_PACKAGES_HOST = "a77a8458-3593-11f0-8426-5e43c8b8aa2f"
# RHEL 10.0 with nodejs (not npm), systemd, ruby, and ansible-core.
RHEL_10_HOST = "1ceccf11-d11b-42f1-be3f-c610f2c1c8d2"
# RHEL 8.1 with nodejs, npm, kernel, and perl.
RHEL_8_HOST = "3796c1ce-aae4-4945-bb3d-9bbe9285a12b"
# RHEL 9.4 and RHEL 9.2, both with openssl and kernel.
RHEL_9_4_HOST = "7b710ce5-d4f5-4ad1-888d-3bf70c8d9cca"
RHEL_9_2_HOST = "75f71dcb-8c89-4b21-8087-4cfc1df7e06a"
# RHEL 8.10 with python3.12 and kernel. The Python item is for RHEL 9.
PYTHON_HOST = "58a63dc1-1896-41f5-bcfe-ed984fd105b3"
# Packages are present, but there is no operating system version.
VERSIONLESS_HOST = "cae1e255-ef1b-4693-b2dc-71e09dd45c00"
UNKNOWN_HOST = "00000000-0000-4000-8000-000000000001"

NODEJS_10 = "Add Node.js to RHEL10 AppStream THIS IS TEST DATA"
SYSTEMD = "Systemd 256 Update THIS IS TEST DATA"
NOBODY = "Test package that nobody has THIS IS TEST DATA"
NODEJS_8 = "Add Node.js to RHEL8 AppStream THIS IS TEST DATA"
KERNEL = "Kernel security update THIS IS TEST DATA"
PERL = "Perl 5.40 EOL THIS IS TEST DATA"
OPENSSL = "OpenSSL 3.2 Update THIS IS TEST DATA"
PYTHON = "Python 3.12 EOL THIS IS TEST DATA"
RUBY = "Ruby 3.3 Deprecation THIS IS TEST DATA"
ANSIBLE = "Ansible Core 2.17 THIS IS TEST DATA"
NOT_DEPLOYED = "Not yet deployed to production item THIS IS TEST DATA"


def _allow(client, host_groups, org_id="1234"):
    """Skip the remote permission call and supply the groups the caller may read."""

    async def get_allowed_host_groups_override():
        return host_groups

    async def decode_header_override():
        return org_id

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override


def _post(client, api_prefix, host_ids, all=False):
    return client.post(
        f"{api_prefix}/relevant/upcoming-changes/hosts",
        json={"host_ids": list(host_ids)},
        params={"all": all},
    )


def _system_ids(item):
    details = item["details"]
    from_detail = {system["id"] for system in details["potentiallyAffectedSystemsDetail"]}
    from_ids = set(details["potentiallyAffectedSystems"])
    assert from_detail == from_ids
    assert details["potentiallyAffectedSystemsCount"] == len(from_detail)
    return from_detail


def _by_name(data):
    names = [item["name"] for item in data]
    assert len(names) == len(set(names)), "Upcoming item names are not unique in this response"
    return {item["name"]: item for item in data}


def _identity(item):
    """Fields that must match between the unscoped endpoint and this host-scoped one."""
    return (
        item["name"],
        item["type"],
        item["release"],
        item["date"],
        tuple(sorted(item["packages"])),
        item["details"]["potentiallyAffectedSystemsCount"],
        tuple(sorted(item["details"]["potentiallyAffectedSystems"])),
        tuple(sorted(system["id"] for system in item["details"]["potentiallyAffectedSystemsDetail"])),
    )


def _known_upcoming_names():
    return {item.name for item in read_upcoming_file(Settings.create().upcoming_json_path)}


def test_relevant_upcoming_for_all_hosts_matches_unscoped(api_prefix, client, read_json_fixture):
    """Every fixture host produces the same payload as the unscoped relevant upcoming endpoint."""
    _allow(client, set())
    host_ids = [host["id"] for host in read_json_fixture("inventory_db_response.json.gz")]

    scoped = _post(client, api_prefix, host_ids)
    unscoped = client.get(f"{api_prefix}/relevant/upcoming-changes")

    assert scoped.status_code == 200, scoped.text
    assert unscoped.status_code == 200, unscoped.text

    scoped_body = scoped.json()
    unscoped_body = unscoped.json()
    data = scoped_body["data"]

    assert scoped_body["meta"] == unscoped_body["meta"]
    assert scoped_body["meta"]["count"] == len(data)
    assert scoped_body["meta"]["total"] == len(data)
    assert all(_system_ids(item) for item in data)
    assert sorted(map(_identity, data)) == sorted(map(_identity, unscoped_body["data"]))


def test_relevant_upcoming_for_all_hosts_matches_unscoped_with_all(api_prefix, client, read_json_fixture):
    """all=true returns the same full catalog for every fixture host and for the unscoped endpoint."""
    _allow(client, set())
    host_ids = [host["id"] for host in read_json_fixture("inventory_db_response.json.gz")]

    scoped = _post(client, api_prefix, host_ids, all=True)
    unscoped = client.get(f"{api_prefix}/relevant/upcoming-changes", params={"all": True})

    assert scoped.status_code == 200, scoped.text
    assert unscoped.status_code == 200, unscoped.text

    scoped_body = scoped.json()
    unscoped_body = unscoped.json()
    data = scoped_body["data"]

    assert scoped_body["meta"] == unscoped_body["meta"]
    assert scoped_body["meta"]["count"] == len(data)
    assert {item["name"] for item in data} == _known_upcoming_names()
    assert any(not _system_ids(item) for item in data)
    assert any(_system_ids(item) for item in data)
    assert sorted(map(_identity, data)) == sorted(map(_identity, unscoped_body["data"]))


def test_relevant_upcoming_for_rhel_10_host_matches_package_intersection(api_prefix, client):
    """nodejs without npm still matches the Node.js item. ruby and ansible-core are RHEL 9 items."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_10_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_10, SYSTEMD}

    nodejs = items[NODEJS_10]
    assert set(nodejs["packages"]) == {"nodejs", "npm"}
    assert _system_ids(nodejs) == {RHEL_10_HOST}
    assert {system["os_major"] for system in nodejs["details"]["potentiallyAffectedSystemsDetail"]} == {10}

    systemd = items[SYSTEMD]
    assert _system_ids(systemd) == {RHEL_10_HOST}
    assert NOBODY not in items
    assert RUBY not in items
    assert ANSIBLE not in items


def test_relevant_upcoming_for_rhel_8_host_matches_major_and_packages(api_prefix, client):
    """The RHEL 8 host matches Node.js, the kernel, and Perl. OpenSSL is installed but is a RHEL 9 item."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_8_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_8, KERNEL, PERL}
    assert set(items[NODEJS_8]["packages"]) == {"nodejs", "npm"}
    assert all(_system_ids(item) == {RHEL_8_HOST} for item in items.values())
    assert OPENSSL not in items


def test_relevant_upcoming_keeps_each_major_on_its_own_items(api_prefix, client):
    """A RHEL 8 host and a RHEL 10 host in one request do not share upcoming items."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_8_HOST, RHEL_10_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_8, KERNEL, PERL, NODEJS_10, SYSTEMD}
    for item in items.values():
        major = int(item["release"].split(".", 1)[0])
        expected = {RHEL_8_HOST} if major == 8 else {RHEL_10_HOST}
        assert _system_ids(item) == expected


def test_relevant_upcoming_merges_hosts_on_the_same_item(api_prefix, client):
    """Two RHEL 9 hosts with openssl are one OpenSSL row. The kernel item is for RHEL 8."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_9_4_HOST, RHEL_9_2_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {OPENSSL}
    assert _system_ids(items[OPENSSL]) == {RHEL_9_4_HOST, RHEL_9_2_HOST}
    assert KERNEL not in items


def test_relevant_upcoming_ignores_package_on_the_wrong_major(api_prefix, client):
    """python3.12 on RHEL 8 does not match the RHEL 9 Python item. The kernel item does match."""
    _allow(client, set())

    result = _post(client, api_prefix, [PYTHON_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {KERNEL}
    assert _system_ids(items[KERNEL]) == {PYTHON_HOST}
    assert PYTHON not in items


def test_relevant_upcoming_all_for_one_host_keeps_unmatched_items(api_prefix, client):
    """all=true returns every known item. Only the two RHEL 10 matches list this host."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_10_HOST], all=True)
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == _known_upcoming_names()
    assert result.json()["meta"] == {"count": len(data), "total": len(data)}

    for name, item in items.items():
        expected = {RHEL_10_HOST} if name in {NODEJS_10, SYSTEMD} else set()
        assert _system_ids(item) == expected

    assert items[NOT_DEPLOYED]["details"]["deployedDate"] is None


def test_relevant_upcoming_skips_versionless_host(api_prefix, client):
    """A host with packages and no OS version is omitted. The RHEL 10 host is still matched."""
    _allow(client, set())

    result = _post(client, api_prefix, [VERSIONLESS_HOST, RHEL_10_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_10, SYSTEMD}
    affected = set().union(*(_system_ids(item) for item in items.values()))
    assert affected == {RHEL_10_HOST}
    assert VERSIONLESS_HOST not in affected


def test_relevant_upcoming_for_host_without_packages(api_prefix, client):
    """A host with an OS version and no packages matches no upcoming item."""
    _allow(client, set())

    result = _post(client, api_prefix, [NO_PACKAGES_HOST])

    assert result.status_code == 200, result.text
    assert result.json() == {"meta": {"count": 0, "total": 0}, "data": []}


def test_relevant_upcoming_ignores_unknown_host_id(api_prefix, client):
    """An id that is not in inventory does not add a system to a real host's items."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_10_HOST, UNKNOWN_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_10, SYSTEMD}
    assert all(_system_ids(item) == {RHEL_10_HOST} for item in items.values())


def test_relevant_upcoming_duplicate_host_ids_count_once(api_prefix, client):
    """Repeating a host id does not count that host twice."""
    _allow(client, set())

    result = _post(client, api_prefix, [RHEL_10_HOST, RHEL_10_HOST])
    data = result.json()["data"]

    assert result.status_code == 200, result.text
    items = _by_name(data)
    assert set(items) == {NODEJS_10, SYSTEMD}
    assert all(item["details"]["potentiallyAffectedSystemsCount"] == 1 for item in items.values())
    assert all(_system_ids(item) == {RHEL_10_HOST} for item in items.values())


def test_relevant_upcoming_omits_hosts_outside_allowed_groups(api_prefix, client):
    """A requested id the caller cannot read is left out of the inventory result."""
    _allow(client, {GROUP_ONE})

    result = _post(client, api_prefix, [NO_PACKAGES_HOST, RHEL_10_HOST])

    assert result.status_code == 200, result.text
    assert result.json()["data"] == []


def test_relevant_upcoming_for_hosts_accepts_empty_list(api_prefix, client):
    """An empty id list is valid and matches no hosts."""
    _allow(client, set())

    result = client.post(
        f"{api_prefix}/relevant/upcoming-changes/hosts",
        json={"host_ids": []},
    )

    assert result.status_code == 200, result.text
    assert result.json() == {"meta": {"count": 0, "total": 0}, "data": []}


def test_relevant_upcoming_for_hosts_no_rbac_access(api_prefix, client):
    async def get_allowed_host_groups_override():
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

    result = _post(client, api_prefix, [RHEL_10_HOST])

    assert result.status_code == 403


def test_relevant_upcoming_for_hosts_database_error(api_prefix, client):
    _allow(client, set())
    session = AsyncMock()
    session.stream.side_effect = DBAPIError("Database connection timeout", None, None)
    client.app.dependency_overrides[get_db] = lambda: session

    result = _post(client, api_prefix, [RHEL_10_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    session.stream.assert_awaited_once()


def test_relevant_upcoming_for_hosts_database_error_while_fetching(api_prefix, client):
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
                    "id": RHEL_10_HOST,
                    "display_name": "rhel-10-host",
                    "os_major": 10,
                    "os_minor": 0,
                    "os_release": "10.0",
                    "packages": ["nodejs-1:22.0.0-1.el10.x86_64"],
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

    result = _post(client, api_prefix, [RHEL_10_HOST])

    assert result.status_code == 500
    assert result.json() == {"detail": "Error querying host inventory"}
    assert "secret_inventory" not in result.text
    assert "sensitive-org" not in result.text
    session.stream.assert_awaited_once()
