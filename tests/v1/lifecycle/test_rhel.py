import uuid

import pytest

from roadmap.common import decode_header
from roadmap.common import query_rbac
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


def test_rhel_relevant(client, api_prefix):
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

    assert len(data) > 1
    assert data[0].keys() == System.model_fields.keys()
    assert len(data[0]["systems"]) > 0  # There should be system IDs
    assert uuid.UUID(data[0]["systems"][0])  # The system ID should be a valid UUID
    for item in data:
        assert item["count"] == len(item["systems"]), "Mismatch between count and number of system IDs"


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
