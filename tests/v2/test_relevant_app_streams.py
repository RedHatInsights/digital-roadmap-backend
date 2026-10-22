from uuid import UUID

import pytest

from fastapi import HTTPException

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream


def _apply_auth_overrides(client):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override


class TestV2AppStreamsRelevantWrapper:
    """Tests for the v2 App Streams relevant list wrapper endpoint."""

    def test_v2_app_streams_relevant_returns_empty_systems(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        for item in data:
            assert item["systems"] == [], f"v2 should return empty systems for {item['display_name']}"
            assert item["systems_detail"] == [], f"v2 should return empty systems_detail for {item['display_name']}"

    def test_v2_app_streams_relevant_counts_match_v1(self, client, v1_prefix, v2_prefix):
        _apply_auth_overrides(client)

        v1_response = client.get(f"{v1_prefix}/relevant/lifecycle/app-streams")
        v2_response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")

        v1_data = v1_response.json()["data"]
        v2_data = v2_response.json()["data"]

        assert len(v1_data) == len(v2_data), "v1 and v2 should return the same number of items"

        v1_counts = {(item["name"], item["os_major"], item.get("os_minor")): item["count"] for item in v1_data}
        v2_counts = {(item["name"], item["os_major"], item.get("os_minor")): item["count"] for item in v2_data}

        assert v1_counts == v2_counts, "v1 and v2 counts must match for all items"

    def test_v2_app_streams_relevant_related(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams?related=true")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        for item in data:
            assert item["systems"] == []
            assert item["systems_detail"] == []

    def test_v2_app_streams_relevant_auth(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        assert result.status_code == 403


class TestV2AppStreamsSystems:
    """Tests for the v2 App Streams systems paginated endpoint."""

    def _get_first_app_stream(self, client, v2_prefix):
        """Helper: fetch v2 list and return the first item with count > 0."""
        _apply_auth_overrides(client)
        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        data = response.json()["data"]
        for item in data:
            if item["count"] > 0:
                return item
        return None

    @staticmethod
    def _systems_params(item, **extra):
        """Build /systems params without sending an empty os_minor query value."""
        params = {"name": item["name"], "os_major": item["os_major"]}
        if item.get("os_minor") is not None:
            params["os_minor"] = item["os_minor"]
        params.update(extra)
        return params

    @staticmethod
    def _override_systems(client, systems_by_stream):
        async def controlled_systems_by_app_stream():
            return systems_by_stream

        client.app.dependency_overrides[systems_by_app_stream] = controlled_systems_by_app_stream

    def test_v2_app_streams_systems_basic(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first),
        )

        assert response.status_code == 200
        data = response.json()
        assert "meta" in data
        assert "data" in data
        assert data["meta"]["count"] == len(data["data"])
        assert data["meta"]["count"] <= 10

    def test_v2_app_streams_systems_pagination(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        params = self._systems_params(first)

        page1 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={**params, "offset": 0, "limit": 2},
        )
        page2 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={**params, "offset": 2, "limit": 2},
        )

        assert page1.status_code == 200
        assert page2.status_code == 200
        assert page1.json()["meta"]["total"] == page2.json()["meta"]["total"]

        page1_ids = {s["id"] for s in page1.json()["data"]}
        page2_ids = {s["id"] for s in page2.json()["data"]}
        if page1_ids and page2_ids:
            assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"

    def test_v2_app_streams_systems_search(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        all_response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, limit=100),
        )

        all_data = all_response.json()["data"]
        assert all_response.status_code == 200
        assert len(all_data) > 0, (
            f"Systems endpoint returned empty data for app stream '{first['name']}' which has count={first['count']}"
        )

        search_term = all_data[0]["display_name"][:5]
        search_response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, search=search_term, limit=100),
        )

        assert search_response.status_code == 200
        for system in search_response.json()["data"]:
            assert search_term.lower() in system["display_name"].lower()

    def test_v2_app_streams_systems_count_consistency(self, client, v2_prefix):
        """Verify list endpoint count matches systems endpoint total."""
        _apply_auth_overrides(client)
        first = None
        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        for item in response.json()["data"]:
            if item["count"] > 0 and item.get("os_minor") is not None:
                first = item
                break
        if first is None:
            pytest.skip("No app streams with concrete os_minor and systems found in test data")

        systems_response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, limit=1),
        )

        assert systems_response.status_code == 200
        assert systems_response.json()["meta"]["total"] == first["count"], (
            f"List count ({first['count']}) does not match systems total "
            f"({systems_response.json()['meta']['total']}) for {first['name']}"
        )

    def test_v2_app_streams_systems_os_minor_none_match(self, client, v2_prefix):
        """An entity with no minor matches both omitted and unmatched minor queries."""
        _apply_auth_overrides(client)

        entity = AppStreamEntity(
            name="wildcard-stream",
            display_name="Wildcard stream",
            stream="1.0",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=None,
        )
        systems = {
            SystemInfo(id=UUID(int=1), display_name="Wildcard host", os_major=9, os_minor=2),
        }
        self._override_systems(client, {AppStreamKey(name="wildcard-stream", app_stream_entity=entity): systems})

        omitted = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "wildcard-stream", "os_major": 9},
        )
        unmatched = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "wildcard-stream", "os_major": 9, "os_minor": 7},
        )

        assert omitted.status_code == 200
        assert unmatched.status_code == 200
        assert omitted.json()["meta"]["total"] == len(systems)
        assert unmatched.json()["meta"]["total"] == len(systems)

    def test_v2_app_streams_systems_exact_match_precedence(self, client, v2_prefix):
        """An exact minor match wins over an entity-level wildcard."""
        _apply_auth_overrides(client)

        wildcard_entity = AppStreamEntity(
            name="controlled-stream",
            display_name="Controlled stream wildcard",
            stream="1.0",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=None,
        )
        exact_entity = AppStreamEntity(
            name="controlled-stream",
            display_name="Controlled stream exact",
            stream="1.0",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=1,
        )
        wildcard_systems = {SystemInfo(id=UUID(int=3), display_name="Wildcard host", os_major=9, os_minor=0)}
        exact_systems = {
            SystemInfo(id=UUID(int=1), display_name="Exact host 1", os_major=9, os_minor=1),
            SystemInfo(id=UUID(int=2), display_name="Exact host 2", os_major=9, os_minor=1),
        }
        self._override_systems(
            client,
            {
                AppStreamKey(name="controlled-stream", app_stream_entity=wildcard_entity): wildcard_systems,
                AppStreamKey(name="controlled-stream", app_stream_entity=exact_entity): exact_systems,
            },
        )

        exact = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "controlled-stream", "os_major": 9, "os_minor": 1},
        )
        fallback = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "controlled-stream", "os_major": 9, "os_minor": 7},
        )

        assert exact.status_code == 200
        assert fallback.status_code == 200
        assert {system["id"] for system in exact.json()["data"]} == {str(system.id) for system in exact_systems}
        assert {system["id"] for system in fallback.json()["data"]} == {str(system.id) for system in wildcard_systems}

    def test_v2_app_streams_systems_omit_minor_unions_integer_minors(self, client, v2_prefix):
        """Omitting os_minor returns all matching integer-minor keys, not empty."""
        _apply_auth_overrides(client)

        minor_zero = AppStreamEntity(
            name="union-stream",
            display_name="Union stream 0",
            stream="1.0",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=0,
        )
        minor_three = AppStreamEntity(
            name="union-stream",
            display_name="Union stream 3",
            stream="1.0",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=3,
        )
        systems_zero = {SystemInfo(id=UUID(int=10), display_name="RHEL 9.0", os_major=9, os_minor=0)}
        systems_three = {
            SystemInfo(id=UUID(int=11), display_name="RHEL 9.3", os_major=9, os_minor=3),
            SystemInfo(id=UUID(int=12), display_name="RHEL 9.3 second", os_major=9, os_minor=3),
        }
        self._override_systems(
            client,
            {
                AppStreamKey(name="union-stream", app_stream_entity=minor_zero): systems_zero,
                AppStreamKey(name="union-stream", app_stream_entity=minor_three): systems_three,
            },
        )

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "union-stream", "os_major": 9},
        )

        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 3
        assert {system["id"] for system in response.json()["data"]} == {
            str(system.id) for system in systems_zero | systems_three
        }

    def test_v2_app_streams_systems_accepts_short_name(self, client, v2_prefix):
        """Short entity names match package keys whose list name includes a stream version."""
        _apply_auth_overrides(client)

        package_entity = AppStreamEntity(
            name="redis",
            application_stream_name="Redis 6",
            display_name="Redis 6",
            stream="6",
            impl=AppStreamImplementation.package,
            os_major=9,
            os_minor=0,
        )
        systems = {SystemInfo(id=UUID(int=20), display_name="Redis host", os_major=9, os_minor=0)}
        self._override_systems(client, {AppStreamKey(name="Redis 6", app_stream_entity=package_entity): systems})

        short_name = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "redis", "os_major": 9},
        )
        list_name = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "Redis 6", "os_major": 9, "os_minor": 0},
        )

        assert short_name.status_code == 200
        assert list_name.status_code == 200
        assert short_name.json()["meta"]["total"] == len(systems)
        assert {system["id"] for system in short_name.json()["data"]} == {
            system["id"] for system in list_name.json()["data"]
        }

    def test_v2_app_streams_systems_openapi_documents_minor_contract(self, client, v2_prefix):
        response = client.get(f"{v2_prefix}/openapi.json")

        assert response.status_code == 200
        operation = response.json()["paths"]["/relevant/lifecycle/app-streams/systems"]["get"]
        assert "union" in operation["description"]
        assert "parent" in operation["description"]
        minor_parameter = next(parameter for parameter in operation["parameters"] if parameter["name"] == "os_minor")
        assert "union" in minor_parameter["description"]
        assert "parent-row count" in minor_parameter["description"]

    def test_v2_app_streams_systems_not_found(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "nonexistent-stream-xyz", "os_major": 99, "os_minor": 99},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []
        assert response.json()["meta"]["total"] == 0

    def test_v2_app_streams_systems_no_rbac_access(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "test", "os_major": 9, "os_minor": 0},
        )
        assert result.status_code == 403

    def test_v2_app_streams_systems_limit_bounds(self, client, v2_prefix):
        """Verify limit min 1 and max 100 are enforced by validation."""
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "test", "os_major": 9, "os_minor": 0, "limit": 0},
        )
        assert response.status_code == 422

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "test", "os_major": 9, "os_minor": 0, "limit": 101},
        )
        assert response.status_code == 422

    def test_v2_app_streams_systems_negative_offset(self, client, v2_prefix):
        """Verify offset min 0 is enforced by validation."""
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "test", "os_major": 9, "os_minor": 0, "offset": -1},
        )
        assert response.status_code == 422
