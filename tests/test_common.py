from contextlib import nullcontext
from datetime import date
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from roadmap.common import _allowed_host_groups_kessel
from roadmap.common import _allowed_host_groups_v1
from roadmap.common import _get_group_list_from_resource_definition
from roadmap.common import _normalize_version
from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import get_allowed_host_groups
from roadmap.common import get_lifecycle_type
from roadmap.common import query_host_inventory
from roadmap.common import query_rbac
from roadmap.common import rhel_major_minor
from roadmap.common import sort_attrs
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import LifecycleType


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
    expected = {
        "id",
        "display_name",
        "os_name",
        "os_minor",
        "os_major",
        "os_release",
        "dnf_modules",
        "packages",
        "products",
    }

    assert len(results) > 1
    assert expected.issubset(results[0])


@pytest.mark.parametrize("major", (7, 8, 9))
async def test_query_host_inventory_major(base_args, major):
    records = await anext(query_host_inventory(**base_args, major=major))
    major_versions = {record["os_major"] async for record in records.mappings()}

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
        major_versions.add(record["os_major"])
        minor_versions.add(record["os_minor"])

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


async def test_query_host_inventory_database_error(base_args, mocker):
    """Test that database errors are caught and converted to HTTPException"""
    mocker.patch.object(
        base_args["session"],
        "stream",
        side_effect=DBAPIError("Database connection timeout", None, None),
    )

    with pytest.raises(HTTPException, match="Error querying host inventory"):
        await anext(query_host_inventory(**base_args))


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


async def test_query_rbac_json_decode_error(mocker):
    settings = Settings(rbac_hostname="example.com")
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(b"invalid json"),
    )

    with pytest.raises(HTTPException, match="Invalid JSON response from RBAC service"):
        await query_rbac(settings)


async def test_query_rbac_generic_exception(mocker):
    settings = Settings(rbac_hostname="example.com")
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=Exception("Connection timeout"),
    )

    with pytest.raises(HTTPException, match="Error communicating with RBAC service"):
        await query_rbac(settings)


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


def test_allowed_host_groups_v1():
    perms = [{"resourceDefinitions": [], "permission": "inventory:*:*"}]
    result = _allowed_host_groups_v1(perms)

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
def test_allowed_host_groups_v1_no_access(permissions):
    with pytest.raises(HTTPException, match="Not authorized to access host inventory"):
        _allowed_host_groups_v1(permissions)


def test_allowed_host_groups_v1_group_read_does_not_501():
    """Regression: inventory:groups:read perms with a group.id resourceDefinition
    must not raise, because an inventory:hosts:read perm grants unrestricted access."""
    permissions = [
        {"permission": "inventory:hosts:read", "resourceDefinitions": []},
        {"permission": "inventory:groups:write", "resourceDefinitions": []},
        {"permission": "inventory:groups:read", "resourceDefinitions": []},
        {
            "permission": "inventory:groups:read",
            "resourceDefinitions": [
                {
                    "attributeFilter": {
                        "key": "group.id",
                        "operation": "in",
                        "value": ["c22abc43-62f9-4a03-94e0-2a49d0e3c3d8"],
                    }
                }
            ],
        },
    ]

    assert _allowed_host_groups_v1(permissions) == set()


@pytest.mark.parametrize(
    ("permissions", "expected"),
    (
        (
            [
                {
                    "permission": "inventory:*:*",
                    "resourceDefinitions": [
                        {
                            "attributeFilter": {
                                "key": "group.id",
                                "operation": "in",
                                "value": ["ebeaf62a-9713-4dad-8d63-32b51cadbda3"],
                            }
                        }
                    ],
                }
            ],
            {"ebeaf62a-9713-4dad-8d63-32b51cadbda3"},
        ),
        (
            [
                {
                    "permission": "inventory:hosts:read",
                    "resourceDefinitions": [
                        {
                            "attributeFilter": {
                                "key": "group.id",
                                "operation": "in",
                                "value": [None, "aec18a86-3593-11f0-8426-5e43c8b8aa2f"],
                            }
                        }
                    ],
                }
            ],
            {None, "aec18a86-3593-11f0-8426-5e43c8b8aa2f"},
        ),
    ),
)
def test_allowed_host_groups_v1_restricted(permissions, expected):
    assert _allowed_host_groups_v1(permissions) == expected


async def test_get_allowed_host_groups_v1_path(mocker):
    """With Kessel disabled (default), get_allowed_host_groups uses RBAC v1."""
    settings = Settings(kessel_enabled=False)
    mocker.patch(
        "roadmap.common.query_rbac",
        return_value=[{"resourceDefinitions": [], "permission": "inventory:*:*"}],
    )

    result = await get_allowed_host_groups(settings=settings, org_id="1234", x_rh_identity=None)

    assert result == set()


async def test_get_allowed_host_groups_kessel_path(mocker):
    """With Kessel enabled, get_allowed_host_groups uses the Kessel path."""
    settings = Settings(kessel_enabled=True)
    kessel_mock = mocker.patch("roadmap.common._allowed_host_groups_kessel", return_value={"grp-1"})
    rbac_mock = mocker.patch("roadmap.common.query_rbac")

    result = await get_allowed_host_groups(settings=settings, org_id="1234", x_rh_identity="header")

    assert result == {"grp-1"}
    kessel_mock.assert_awaited_once()
    rbac_mock.assert_not_called()


async def test_allowed_host_groups_kessel_dev_mode():
    """Dev mode short-circuits to unrestricted without contacting Kessel."""
    settings = Settings(kessel_enabled=True, dev=True)

    result = await _allowed_host_groups_kessel(settings, org_id="1234", x_rh_identity=None)

    assert result == set()


async def test_allowed_host_groups_kessel_unrestricted(mocker):
    """A user with access to the org's default workspace has unrestricted access."""
    settings = Settings(kessel_enabled=True)
    mocker.patch("roadmap.kessel.subject_from_identity", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.get_client", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.host_groups_for", return_value=["root-ws", "grp-1"])
    mocker.patch("roadmap.kessel.org_wide_workspace_ids", return_value=frozenset({"root-ws", "default-ws"}))

    result = await _allowed_host_groups_kessel(settings, org_id="1234", x_rh_identity=None)

    assert result == set()


async def test_allowed_host_groups_kessel_scoped(mocker):
    """A workspace-scoped user gets the set of standard workspace ids."""
    settings = Settings(kessel_enabled=True)
    mocker.patch("roadmap.kessel.subject_from_identity", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.get_client", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.host_groups_for", return_value=["grp-1", "grp-2"])
    mocker.patch("roadmap.kessel.org_wide_workspace_ids", return_value=frozenset({"root-ws", "default-ws"}))

    result = await _allowed_host_groups_kessel(settings, org_id="1234", x_rh_identity=None)

    assert result == {"grp-1", "grp-2"}


async def test_allowed_host_groups_kessel_denied(mocker):
    """A user with no accessible workspaces is denied."""
    settings = Settings(kessel_enabled=True)
    mocker.patch("roadmap.kessel.subject_from_identity", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.get_client", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.host_groups_for", return_value=[])

    with pytest.raises(HTTPException, match="Not authorized to access host inventory"):
        await _allowed_host_groups_kessel(settings, org_id="1234", x_rh_identity=None)


async def test_allowed_host_groups_kessel_service_error(mocker):
    """A Kessel communication failure surfaces as a 502."""
    settings = Settings(kessel_enabled=True)
    mocker.patch("roadmap.kessel.subject_from_identity", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.get_client", return_value=mocker.Mock())
    mocker.patch("roadmap.kessel.host_groups_for", side_effect=Exception("gRPC unavailable"))

    with pytest.raises(HTTPException, match="Error communicating with authorization service"):
        await _allowed_host_groups_kessel(settings, org_id="1234", x_rh_identity=None)


def test_sort_attrs(mocker):
    """Given an object with attributes that are an empty string, None, and non-null
    value, ensure the expected tuple of values are returned."""

    obj = mocker.Mock(empty="", none=None, real="real")
    sorter = sort_attrs("empty", "none", "real")
    result = sorter(obj)

    assert result == (-1, -2, "real")


@pytest.mark.parametrize(
    "stream, expected",
    [
        ("rhel8", (8, 0, 0)),
        ("8", (8, 0, 0)),
        ("10.7.3", (10, 7, 3)),
        ("2", (2, 0, 0)),
    ],
)
def test_normalize_version(stream, expected):
    result = _normalize_version(stream)

    assert result == expected


@pytest.mark.parametrize(
    "profile, expected, context",
    (
        ({"os_major": 9, "os_minor": 0}, (9, 0), nullcontext()),
        ({"name": "RHEL", "os_release": "9.0"}, (9, 0), nullcontext()),
        ({"name": "RHEL", "os_release": "9.1.10"}, (9, 1), nullcontext()),
        ({"os_release": "9.2"}, (9, 2), nullcontext()),
        ({}, None, pytest.raises(ValueError)),
    ),
)
def test_rhel_major_minor(profile, expected, context):
    with context:
        result = rhel_major_minor(profile)

        # The assert statement is placed inside the context manager so that it
        # does not execute in scenarios where exceptions are raised.
        #
        # It is almost always incorrect to do this, but is intentional in this case.
        #
        # https://docs.pytest.org/en/6.2.x/reference.html#pytest.raises
        assert result == expected


@pytest.mark.parametrize(
    "products, expected",
    (
        # Mainline — no recognized product IDs
        ([{}], LifecycleType.mainline),
        ([{"id": "999"}], LifecycleType.mainline),
        # Mainline — base RHEL product (must NOT trigger E4S)
        ([{"id": "479"}], LifecycleType.mainline),
        # EUS
        ([{"id": "70"}], LifecycleType.eus),
        ([{"id": "73"}], LifecycleType.eus),
        ([{"id": "75"}], LifecycleType.eus),
        # ELS
        ([{"id": "204"}], LifecycleType.els),
        # E4S — existing product IDs
        ([{"id": "241"}], LifecycleType.e4s),
        ([{"id": "323"}], LifecycleType.e4s),
        # E4S — SAP product IDs per rhsm-subscriptions rhel_for_sap_x86.yaml (RHINENG-27803)
        ([{"id": "146"}], LifecycleType.e4s),
        ([{"id": "388"}], LifecycleType.e4s),
        ([{"id": "389"}], LifecycleType.e4s),
        # Hierarchy: E4S wins over EUS
        ([{"id": "70"}, {"id": "388"}], LifecycleType.e4s),
        # Hierarchy: E4S wins over ELS
        ([{"id": "204"}, {"id": "241"}], LifecycleType.e4s),
        # Hierarchy: ELS wins over EUS
        ([{"id": "70"}, {"id": "204"}], LifecycleType.els),
        # Real SAP system combo: 388 + 389 + 479 (generic RHEL base)
        ([{"id": "388"}, {"id": "389"}, {"id": "479"}], LifecycleType.e4s),
        # Base RHEL + EUS — 479 does not upgrade beyond EUS
        ([{"id": "479"}, {"id": "70"}], LifecycleType.eus),
    ),
)
def test_get_lifecycle_type(products, expected):
    result = get_lifecycle_type(products)

    assert result == expected
