from datetime import date
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fastapi import HTTPException

from roadmap.common import check_inventory_access
from roadmap.common import decode_header
from roadmap.common import ensure_date
from roadmap.common import query_host_inventory
from roadmap.common import query_rbac
from roadmap.config import Settings


@pytest.mark.xfail
async def test_query_host_inventory(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await query_host_inventory(headers)

    assert len(response["results"]) > 1
    assert response["count"] == 100


@pytest.mark.xfail
async def test_query_host_inventory_major(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response_9.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await query_host_inventory(headers, major=9)
    versions = {item["system_profile"]["operating_system"]["major"] for item in response["results"]}

    assert len(response["results"]) > 1
    assert versions == {9}


@pytest.mark.xfail
async def test_query_host_inventory_major_minor(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response_9.5.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await query_host_inventory(headers, major=9, minor=5)
    major_versions = {item["system_profile"]["operating_system"]["major"] for item in response["results"]}
    minor_versions = {item["system_profile"]["operating_system"]["minor"] for item in response["results"]}

    assert len(response["results"]) > 1
    assert major_versions == {9}, "Major version mismatch"
    assert minor_versions == {5}, "Minor version mismatch"


@pytest.mark.xfail
async def test_query_host_inventory_major_minor_zero(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response_9.0.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await query_host_inventory(headers, major=9, minor=0)
    major_versions = {item["system_profile"]["operating_system"]["major"] for item in response["results"]}
    minor_versions = {item["system_profile"]["operating_system"]["minor"] for item in response["results"]}

    assert len(response["results"]) > 1
    assert major_versions == {9}, "Major version mismatch"
    assert minor_versions == {0}, "Minor version mismatch"


@pytest.mark.xfail
async def test_query_host_inventory_missing_auth():
    result = await query_host_inventory({})

    assert result == {}


@pytest.mark.xfail
async def test_query_host_inventory_missing_none_filter(mocker):
    mocker.patch("roadmap.common.urllib.request.urlopen", side_effect=ValueError("Raised intentionally"))
    mock_req = mocker.patch("roadmap.common.urllib.request.Request")
    headers = {
        "Authorization": "Bearer token",
        "Value": None,
    }
    with pytest.raises(ValueError, match="Raised intentionally"):
        await query_host_inventory(headers)

    assert mock_req.call_args.kwargs["headers"] == {"Authorization": "Bearer token"}


@pytest.mark.xfail
@pytest.mark.parametrize(
    ("major", "minor"),
    (
        (9, None),
        (8, 0),
    ),
)
async def test_query_host_inventory_dev_mode(mocker, major, minor):
    mocker.patch("roadmap.common.SETTINGS.dev", True)
    mocker.patch("roadmap.common.urllib.request.urlopen", side_effect=ValueError("Should not get here"))

    result = await query_host_inventory({}, major=major, minor=minor)

    assert len(result) > 0


@pytest.mark.xfail
async def test_query_host_inventory_error(mocker):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=HTTPError(url="url", code=401, hdrs=Message(), msg="Unauthorized", fp=BytesIO()),
    )

    with pytest.raises(HTTPException):
        await query_host_inventory({"Authorization": "Bearer token"})


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


async def test_check_inventory_access():
    result = await check_inventory_access([{"resourceDefinitions": [], "permission": "inventory:*:*"}])

    assert result == []


@pytest.mark.parametrize(
    "permissions",
    (
        [],
        [{"resourceDefinitions": ["def1"]}],
        [{"resourceDefinitions": [], "permission": "nope"}],
    ),
)
async def test_check_inventory_no_access(permissions):
    with pytest.raises(HTTPException):
        await check_inventory_access(permissions)
