from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fastapi import HTTPException

from roadmap.common import get_system_count_from_inventory


async def test_get_system_count_from_inventory(mocker, read_fixture_file):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        return_value=BytesIO(read_fixture_file("inventory_response.json", mode="rb")),
    )
    headers: dict[str, str | None] = {"Authorization": "Bearer token"}
    response = await get_system_count_from_inventory(headers)

    assert len(response["results"]) > 1
    assert response["count"] == 100


async def test_get_system_count_from_inventory_missing_auth():
    result = await get_system_count_from_inventory({})

    assert result == {}


async def test_get_system_count_from_inventory_missing_none_filter(mocker):
    mocker.patch("roadmap.common.urllib.request.urlopen", side_effect=ValueError("Raised intentionally"))
    mock_req = mocker.patch("roadmap.common.urllib.request.Request")
    headers = {
        "Authorization": "Bearer token",
        "Value": None,
    }
    with pytest.raises(ValueError, match="Raised intentionally"):
        await get_system_count_from_inventory(headers)

    assert mock_req.call_args.kwargs["headers"] == {"Authorization": "Bearer token"}


async def test_get_system_count_from_inventory_dev_mode(mocker):
    mocker.patch("roadmap.common.SETTINGS.dev", True)
    mocker.patch("roadmap.common.urllib.request.urlopen", side_effect=ValueError("Should not get here"))

    result = await get_system_count_from_inventory({})

    assert len(result) > 0


async def test_get_system_count_from_inventory_error(mocker):
    mocker.patch(
        "roadmap.common.urllib.request.urlopen",
        side_effect=HTTPError(url="url", code=401, hdrs=Message(), msg="Unauthorized", fp=BytesIO()),
    )

    with pytest.raises(HTTPException):
        await get_system_count_from_inventory({"Authorization": "Bearer token"})
