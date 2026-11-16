"""The host_ids request body is bounded.

Every POST endpoint that takes a list of host ids shares HostIdsRequest. The
list is parsed into UUID objects and then bound as a Postgres array, so an
unbounded list lets the caller choose how much memory the request costs. These
tests pin the cap at the model and at each route that uses it.
"""

import uuid

import pytest

from pydantic import ValidationError

from roadmap.common import get_allowed_host_groups
from roadmap.models import HostIdsRequest
from roadmap.models import MAX_HOST_IDS


HOST_ID_ROUTES = (
    "/api/roadmap/v1/relevant/lifecycle/rhel/hosts",
    "/api/roadmap/v1/relevant/lifecycle/app-streams/hosts",
    "/api/roadmap/v1/relevant/upcoming-changes/hosts",
)

#: Largest batch the console UI posts, from BATCH_SIZE in the frontend's
#: relevantRhelLoader.ts. Upcoming and app streams use 1000.
FRONTEND_MAX_BATCH = 5_000


def _ids(count: int) -> list[str]:
    """A list of distinct, well-formed host ids."""
    return [str(uuid.UUID(int=n)) for n in range(count)]


class TestModel:
    def test_at_the_cap_is_valid(self):
        request = HostIdsRequest(host_ids=_ids(MAX_HOST_IDS))

        assert len(request.host_ids) == MAX_HOST_IDS

    def test_over_the_cap_is_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            HostIdsRequest(host_ids=_ids(MAX_HOST_IDS + 1))

    def test_the_largest_frontend_batch_fits(self):
        """The cap must not reject what the console UI already sends."""
        assert FRONTEND_MAX_BATCH <= MAX_HOST_IDS

        request = HostIdsRequest(host_ids=_ids(FRONTEND_MAX_BATCH))

        assert len(request.host_ids) == FRONTEND_MAX_BATCH

    def test_empty_list_is_still_accepted(self):
        """An empty list is a meaningful request: it matches no hosts."""
        assert HostIdsRequest(host_ids=[]).host_ids == []


class TestRoutes:
    """The cap is enforced on the wire, not just in the model."""

    @pytest.fixture()
    def permitted_client(self, client):
        """Client whose permission check is already satisfied.

        Without this the request is turned away by authorization first and the
        test would pass for the wrong reason. No database override is needed:
        an over-long body is rejected before the endpoint runs a query.
        """

        async def unrestricted_groups():
            return set()

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = unrestricted_groups
        yield client
        client.app.dependency_overrides = {}

    @pytest.mark.parametrize("route", HOST_ID_ROUTES)
    def test_over_the_cap_returns_422(self, permitted_client, route):
        response = permitted_client.post(route, json={"host_ids": _ids(MAX_HOST_IDS + 1)})

        assert response.status_code == 422
        assert "host_ids" in response.text
