from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fastapi import HTTPException

from roadmap.common import query_host_inventory


async def test_query_host_inventory(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await query_host_inventory(headers)

    assert len(response["results"]) > 1
    assert response["count"] == 100


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


async def test_query_host_inventory_missing_auth():
    result = await query_host_inventory({})

    assert result == {}


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


async def test_query_host_inventory_error(mocker):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=HTTPError(url="url", code=401, hdrs=Message(), msg="Unauthorized", fp=BytesIO()),
    )

    with pytest.raises(HTTPException):
        await query_host_inventory({"Authorization": "Bearer token"})
