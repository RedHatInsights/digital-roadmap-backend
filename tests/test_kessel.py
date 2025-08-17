from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from roadmap.kessel import KesselClient
from roadmap.kessel import ObjectType
from roadmap.kessel import Resource


@pytest.fixture()
async def kessel_client():
    kessel_client = KesselClient("localhost")
    kessel_client.channel = MagicMock(kessel_client.channel)
    kessel_client.stub = MagicMock(kessel_client.stub)

    async def streamed_list_objects(request):
        continuation_token = request.pagination.continuation_token or None
        if continuation_token is None:
            yield SimpleNamespace(object=SimpleNamespace(), pagination=SimpleNamespace(continuation_token="1"))
            yield SimpleNamespace(object=SimpleNamespace(), pagination=SimpleNamespace(continuation_token="2"))
        elif continuation_token == "2":
            yield SimpleNamespace(object=SimpleNamespace(), pagination=SimpleNamespace(continuation_token="3"))
        elif continuation_token == "3":
            pass
        else:
            raise ValueError("Should not reach this point - Test is wrong")

    kessel_client.stub.StreamedListObjects.side_effect = streamed_list_objects

    return kessel_client


async def exhaust_async_iterator(generator):
    return [i async for i in generator]


async def test_get_resources(kessel_client):
    found = await exhaust_async_iterator(
        kessel_client.get_resources(ObjectType.workspace(), "relation_a", Resource.principal("foobar"))
    )
    kessel_client.stub.StreamedListObjects.assert_called()
    assert len(found) == 3
