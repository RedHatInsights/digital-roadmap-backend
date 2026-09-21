import uuid

import pytest

from fastapi import HTTPException

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import System


def test_rhel_lifecycle(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel")
    data = response.json()["data"]
    names = {item.get("name") for item in data}

    assert len(data) > 0
    assert names == {"RHEL"}
    assert any(item["minor"] is None for item in data), "Full lifecycle data is missing from the response"
    assert response.status_code == 200


def test_rhel_lifecycle_major_version(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel/9")
    data = response.json()["data"]
    names = {item.get("name") for item in data}
    versions = {item.get("major") for item in data}

    assert len(data) > 0
    assert names == {"RHEL"}
    assert versions == {9}
    assert response.status_code == 200


@pytest.mark.parametrize("params", ("9/0", "9/1", "8/2", "8/0"))
def test_rhel_lifecycle_major_minor_version(client, api_prefix, params):
    response = client.get(f"{api_prefix}/lifecycle/rhel/{params}")
    data = response.json()["data"]
    names = {item.get("name") for item in data}
    major = data[0]["major"]
    minor = data[0]["minor"]

    assert response.status_code == 200
    assert len(data) == 1
    assert names == {"RHEL"}
    assert (major, minor) == tuple(int(v) for v in params.split("/"))


def test_rhel_lifecycle_full(client, api_prefix):
    response = client.get(f"{api_prefix}/lifecycle/rhel/full")
    data = response.json()["data"]
    minor_versions = set(item["minor"] for item in data)

    assert response.status_code == 200
    assert minor_versions == {None}


@pytest.mark.parametrize("os_major", (8, 9))
def test_rhel_lifecycle_full_major(client, api_prefix, os_major):
    response = client.get(f"{api_prefix}/lifecycle/rhel/full/{os_major}")
    data = response.json()["data"]
    major_versions = set(item["major"] for item in data)
    minor_versions = set(item["minor"] for item in data)

    assert response.status_code == 200
    assert major_versions == {os_major}
    assert minor_versions == {None}


def test_rhel_relevant(client, api_prefix, ids_by_os):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    response = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    data = response.json()["data"]
    rhel_9_1_mainline = [
        item for item in data if (9, 1, "mainline") == (item["major"], item["minor"], item["lifecycle_type"])
    ]
    rhel_9_1_mainline = set(rhel_9_1_mainline[0]["systems"])

    assert len(data) > 1
    assert data[0].keys() == System.model_fields.keys()
    assert len(data[0]["systems"]) > 0, "There should be system IDs"
    assert uuid.UUID(data[0]["systems"][0]), "The system ID should be a valid UUID"
    assert rhel_9_1_mainline == ids_by_os["9.1"]
    for item in data:
        assert item["count"] == len(item["systems"]), "Mismatch between count and number of system IDs"


def test_rhel_relevant_extended_dates(client, api_prefix):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    response = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    data = response.json()["data"]
    extended_dates = [n for n in data if n["lifecycle_type"] != "mainline"]

    for item in extended_dates:
        key = f"{item['major']}.{item['minor']}"
        attr = f"end_date_{item['lifecycle_type'].lower()}"
        expected = getattr(OS_LIFECYCLE_DATES[key], attr)
        assert item["end_date"] == expected.isoformat(), (
            f"Incorrect end_date for a RHEL {key} {item['lifecycle_type']} host"
        )


def test_get_relevant_rhel_no_rbac_access(api_prefix, client):
    async def get_allowed_host_groups_override():
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert result.status_code == 403


def test_rhel_relevant_related(client, api_prefix):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    response = client.get(f"{api_prefix}/relevant/lifecycle/rhel?related=true")
    data = response.json()["data"]
    related_hosts = [item for item in data if not item["count"]]

    assert len(data) > 1
    assert len(related_hosts) > 1
    assert all([len(set(item["systems"])) == len(item["systems"]) for item in data]), (
        "Found duplicate system IDs in results"
    )


def test_rhel_relevant_second_request_is_cached(client, api_prefix, mocker):
    """A repeated request is served from the cache instead of being rebuilt."""

    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    first = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    assert first.status_code == 200

    # Building the response again would now raise, so a successful second
    # response can only have come from the cache.
    mocker.patch("roadmap.v1.lifecycle.rhel.System", side_effect=ValueError("Raised intentionally"))
    second = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert second.status_code == 200
    assert second.json() == first.json()


def test_rhel_relevant_related_is_not_served_from_the_unrelated_cache(client, api_prefix):
    """The cache is keyed on 'related', so the two variants do not share an entry."""

    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    unrelated = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    related = client.get(f"{api_prefix}/relevant/lifecycle/rhel?related=true")

    assert unrelated.status_code == 200
    assert related.status_code == 200
    assert related.json() != unrelated.json(), "The related response was served from the unrelated cache entry"


def test_rhel_relevant_cache_is_per_org(client, api_prefix):
    """A second org does not receive the first org's cached response."""
    org_ids = iter(("1234", "5678"))

    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return next(org_ids)

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    first = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    second = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["data"]) > 0, "The first org should have systems for this test to be meaningful"
    assert second.json()["data"] != first.json()["data"], "The second org was served the first org's cached response"


def test_rhel_relevant_cache_is_per_permission_scope(client, api_prefix):
    """A restricted caller is not served an unrestricted caller's cached response.

    Two users in one org can have different host group permissions, so the
    permissions have to be part of the cache key.
    """
    # An empty set means unrestricted. The group id matches no host, so the
    # second caller is entitled to see nothing.
    host_groups = iter((set(), {str(uuid.uuid4())}))

    async def get_allowed_host_groups_override():
        return next(host_groups)

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    unrestricted = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    restricted = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert unrestricted.status_code == 200
    assert restricted.status_code == 200
    assert len(unrestricted.json()["data"]) > 0, "The first caller should see systems for this test to be meaningful"
    assert restricted.json()["data"] == [], "The restricted caller was served the unrestricted cached response"


def test_rhel_relevant_response_too_large_to_cache(client, api_prefix, monkeypatch, mocker):
    """A response bigger than the whole cache budget is still served, just not cached."""
    monkeypatch.setenv("ROADMAP_LIFECYCLE_CACHE_MAX_BYTES", "1")

    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    first = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    assert first.status_code == 200
    assert len(first.json()["data"]) > 0, "There should be systems for this test to be meaningful"

    # Nothing was cached, so the second response has to be built from scratch
    # and the raising mock is reached. A cache hit would return 200 instead.
    mocker.patch("roadmap.v1.lifecycle.rhel.System", side_effect=ValueError("Raised intentionally"))
    with pytest.raises(ValueError, match="Raised intentionally"):
        client.get(f"{api_prefix}/relevant/lifecycle/rhel")


@pytest.mark.parametrize(("first_major", "second_major"), ((9, 8), (8, 9)))
def test_rhel_relevant_cache_is_per_major_version(client, api_prefix, first_major, second_major):
    """A request filtered to one major version is not served another version's response."""

    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override

    first = client.get(f"{api_prefix}/relevant/lifecycle/rhel?major={first_major}")
    second = client.get(f"{api_prefix}/relevant/lifecycle/rhel?major={second_major}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert {item["major"] for item in first.json()["data"]} == {first_major}
    assert {item["major"] for item in second.json()["data"]} == {second_major}, (
        "The second request was served the first major version's cached response"
    )
