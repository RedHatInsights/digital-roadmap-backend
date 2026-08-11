import uuid

import pytest

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import get_db
from roadmap.common import query_rbac
from roadmap.config import Settings
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import System
from roadmap.services import relevant_cache as cache_module


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


def test_rhel_relevant_response_cache_hit_and_ttl_expiry(client, api_prefix, monkeypatch):
    async def query_rbac_override():
        return [{"permission": "inventory:*:*", "resourceDefinitions": []}]

    async def decode_header_override():
        return "1234"

    async def get_allowed_host_groups_override():
        return {"group-a"}

    async def get_db_override():
        yield object()

    settings = Settings(dev=True, relevant_cache_ttl_seconds=1, relevant_cache_maxsize=32)
    timeline = iter([0.0, 0.1, 0.2, 1.5, 1.6])
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: next(timeline))
    monkeypatch.setattr(cache_module.relevant_response_cache, "_entries", {})

    rows = [
        {
            "id": "02f7e6ea-a0f6-4a98-b857-b0e9f9f0f111",
            "display_name": "cache-host",
            "os_name": "RHEL",
            "os_major": 9,
            "os_minor": 2,
            "os_release": "9.2",
            "dnf_modules": [],
            "packages": [],
            "products": [],
        }
    ]
    load_calls = {"count": 0}

    async def fake_load_host_inventory_rows(*args, **kwargs):
        load_calls["count"] += 1
        return rows

    monkeypatch.setattr(
        "roadmap.v1.lifecycle.rhel.load_host_inventory_rows",
        fake_load_host_inventory_rows,
    )

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override
    client.app.dependency_overrides[decode_header] = decode_header_override
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[get_db] = get_db_override
    client.app.dependency_overrides[Settings.create] = lambda: settings

    first = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    second = client.get(f"{api_prefix}/relevant/lifecycle/rhel")
    third = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert load_calls["count"] == 2, "Expected one cache hit between two misses"


def test_rhel_relevant_extended_dates(client, api_prefix):
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
    async def query_rbac_override():
        return [{}]

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[query_rbac] = query_rbac_override

    result = client.get(f"{api_prefix}/relevant/lifecycle/rhel")

    assert result.status_code == 403


def test_rhel_relevant_related(client, api_prefix):
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

    response = client.get(f"{api_prefix}/relevant/lifecycle/rhel?related=true")
    data = response.json()["data"]
    related_hosts = [item for item in data if not item["count"]]

    assert len(data) > 1
    assert len(related_hosts) > 1
    assert all([len(set(item["systems"])) == len(item["systems"]) for item in data]), (
        "Found duplicate system IDs in results"
    )
