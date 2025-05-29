from datetime import date
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fastapi import HTTPException

from roadmap.common import _get_group_list_from_resource_definition
from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_host_inventory
from roadmap.common import query_rbac
from roadmap.common import sort_attrs
from roadmap.config import Settings
from roadmap.database import get_db


@pytest.fixture(scope="module")
async def base_args():
    settings = Settings.create()
    session = await anext(get_db())
    return {
        "org_id": "1234",
        "session": session,
        "settings": settings,
        "host_groups": [],
    }


async def test_query_host_inventory(base_args):
    records = await anext(query_host_inventory(**base_args))
    results = [item async for item in records.mappings()]

    assert len(results) > 1
    assert "system_profile_facts" in results[0]


@pytest.mark.parametrize("major", (7, 8, 9))
async def test_query_host_inventory_major(base_args, major):
    records = await anext(query_host_inventory(**base_args, major=major))

    major_versions = set()
    async for record in records.mappings():
        if system_profile := record.get("system_profile_facts"):
            if major_version := system_profile.get("operating_system", {}).get("major"):
                major_versions.add(major_version)

    assert major_versions == {major}


@pytest.mark.parametrize(
    ("major", "minor"),
    (
        (9, 5),
        (9, 0),
        (8, 1),
        (8, 0),
    ),
)
async def test_query_host_inventory_major_minor(base_args, major, minor):
    records = await anext(query_host_inventory(**base_args, major=major, minor=minor))
    major_versions = set()
    minor_versions = set()
    async for record in records.mappings():
        if system_profile := record.get("system_profile_facts"):
            if major_version := system_profile.get("operating_system", {}).get("major"):
                major_versions.add(major_version)

            if (minor_version := system_profile.get("operating_system", {}).get("minor")) is not None:
                minor_versions.add(minor_version)

    assert major_versions == {major}, "Major version mismatch"
    assert minor_versions == {minor}, "Minor version mismatch"


async def test_query_host_inventory_dev(base_args):
    """In dev mode with no org ID set, test that records are returned"""
    settings = Settings(dev=True)
    records = await anext(query_host_inventory(**base_args | {"settings": settings, "org_id": None}))
    results = [item async for item in records.mappings()]

    assert len(results) > 1


@pytest.mark.parametrize(
    ("org_id", "expected"),
    (
        ("8765309", 20),
        (None, 20),
    ),
)
async def test_query_host_inventory_dev_org_id(base_args, org_id, expected):
    """In dev mode with an org_id, test that expected records are returnd

    The test data only has records for org_id 1234, which should be always set as default in dev mode.
    """
    settings = Settings(dev=True)
    records = await anext(query_host_inventory(**base_args | {"settings": settings, "org_id": org_id}))
    results = [item async for item in records.mappings()]

    assert len(results) > expected


@pytest.mark.parametrize("date_string", ("20250101", "2025-01-01"))
def test_ensure_date(date_string):
    result = ensure_date(date_string)

    assert result == date(2025, 1, 1)


@pytest.mark.parametrize("date_string", (1_000, "101"))
def test_ensure_date_error(date_string):
    with pytest.raises((ValueError, TypeError), match="Date must be"):
        ensure_date(date_string)


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (None, ""),
        (b"eyJpZGVudGl0eSI6IHsib3JnX2lkIjogIjMxNDE1OTcifX0=", "3141597"),
    ),
)
async def test_decode_header(value, expected):
    result = await decode_header(value)

    assert result == expected


async def test_query_rbac(mocker, read_fixture_file):
    settings = Settings(rbac_hostname="example.com")
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("rbac_response.json", mode="rb")),
    )

    result = await query_rbac(settings)

    assert result == [{"permission": "inventory:*:*:foo", "resourceDefinitions": []}]


async def test_query_rbac_error(mocker):
    settings = Settings(rbac_hostname="example.com")
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=HTTPError(url="url", code=401, hdrs=Message(), msg="Raised intentionally", fp=BytesIO()),
    )

    with pytest.raises(HTTPException, match="Raised intentionally"):
        await query_rbac(settings)


async def test_query_rbac_dev_mode():
    settings = Settings(dev=True)

    result = await query_rbac(settings)

    assert result == [{"permission": "inventory:*:*", "resourceDefinitions": []}]


async def test_query_rbac_no_url():
    settings = Settings(rbac_hostname="")

    result = await query_rbac(settings)

    assert result == [{}]


@pytest.mark.parametrize(
    ("resource_definition", "expected"),
    (
        (
            {
                "attributeFilter": {
                    "key": "group.id",
                    "operation": "in",
                    "value": ["80d9581f-e6d9-4b78-aa2c-d0bfdf35fc51", None],
                }
            },
            ["80d9581f-e6d9-4b78-aa2c-d0bfdf35fc51", None],
        ),
        (
            {
                "attributeFilter": {
                    "key": "group.id",
                    "operation": "equal",
                    "value": "80d9581f-e6d9-4b78-aa2c-d0bfdf35fc51",
                }
            },
            ["80d9581f-e6d9-4b78-aa2c-d0bfdf35fc51"],
        ),
    ),
)
def test_get_group_list_from_resource_definition(resource_definition, expected):
    result = _get_group_list_from_resource_definition(resource_definition)

    assert result == expected


@pytest.mark.parametrize(
    "resource_definition",
    (
        {},
        {"attributeFilter": {"key": "nope"}},
        {"attributeFilter": {"key": "group.id", "operation": "nope"}},
        {"attributeFilter": {"key": "group.id", "operation": "in", "value": "should be a list"}},
        {"attributeFilter": {"key": "group.id", "operation": "equal", "value": ["should be a string"]}},
        {"attributeFilter": {"key": "group.id", "operation": "equal", "value": "bad UUID"}},
    ),
)
def test_get_group_list_from_resource_definition_error(resource_definition):
    with pytest.raises(HTTPException):
        _get_group_list_from_resource_definition(resource_definition)


async def test_get_allowed_host_groups():
    perms = [{"resourceDefinitions": [], "permission": "inventory:*:*"}]
    result = await get_allowed_host_groups(perms)

    # Empty set means unrestricted access.
    assert result == set()


@pytest.mark.parametrize(
    "permissions",
    (
        [],
        [{"resourceDefinitions": []}],
        [{"resourceDefinitions": [], "permission": "nope"}],
    ),
)
async def test_get_allowed_host_groups_no_access(permissions):
    with pytest.raises(HTTPException, match="Not authorized to access host inventory"):
        await get_allowed_host_groups(permissions)


def test_sort_attrs(mocker):
    """Given an object with attributes that are an empty string, None, and non-null
    value, ensure the expected tuple of values are returned."""

    obj = mocker.Mock(empty="", none=None, real="real")
    sorter = sort_attrs("empty", "none", "real")
    result = sorter(obj)

    assert result == (-1, -2, "real")
