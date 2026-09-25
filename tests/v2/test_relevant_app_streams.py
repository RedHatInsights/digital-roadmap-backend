import pytest

from fastapi import HTTPException

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups


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
        """Build query params for the /systems endpoint, omitting os_minor when None."""
        params = {"name": item["name"], "os_major": item["os_major"]}
        if item.get("os_minor") is not None:
            params["os_minor"] = item["os_minor"]
        params.update(extra)
        return params

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

        base_params = self._systems_params(first)

        page1 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={**base_params, "offset": 0, "limit": 2},
        )
        page2 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={**base_params, "offset": 2, "limit": 2},
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
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        systems_response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, limit=1),
        )

        assert systems_response.status_code == 200
        assert systems_response.json()["meta"]["total"] == first["count"], (
            f"List count ({first['count']}) does not match systems total "
            f"({systems_response.json()['meta']['total']}) for {first['name']}"
        )

    def test_v2_app_streams_systems_not_found(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "nonexistent-stream-xyz", "os_major": 99, "os_minor": 99},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []
        assert response.json()["meta"]["total"] == 0

    def test_v2_app_streams_systems_os_minor_none_match(self, client, v2_prefix):
        """Verify systems are found for app streams whose entity has os_minor=None.

        Some app streams (e.g. Container Tools, Python 3.6) span multiple minor
        versions and have os_minor=None in their entity definition. The /systems
        endpoint must still return their hosts regardless of whether the caller
        sends os_minor=<int> or omits it entirely.
        """
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        data = response.json()["data"]
        target = None
        for item in data:
            if item.get("os_minor") is None and item.get("count", 0) > 0:
                target = item
                break

        if target is None:
            pytest.skip("No app streams with os_minor=None and count>0 in test data")

        # Case 1: omit os_minor — should match
        r1 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": target["name"], "os_major": target["os_major"], "limit": 1},
        )
        assert r1.status_code == 200
        assert r1.json()["meta"]["total"] == target["count"], (
            f"Omitting os_minor should match os_minor=None entity, "
            f"expected {target['count']} but got {r1.json()['meta']['total']}"
        )

        # Case 2: send os_minor=0 — should still match (entity is version-agnostic)
        r2 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": target["name"], "os_major": target["os_major"], "os_minor": 0, "limit": 1},
        )
        assert r2.status_code == 200
        assert r2.json()["meta"]["total"] == target["count"], (
            f"Sending os_minor=0 should match os_minor=None entity, "
            f"expected {target['count']} but got {r2.json()['meta']['total']}"
        )

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

    def test_v2_app_streams_systems_sort_order_asc(self, client, v2_prefix):
        """Verify sort_order=asc returns systems sorted ascending."""
        _apply_auth_overrides(client)
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, limit=100, sort_order="asc"),
        )
        assert response.status_code == 200
        names = [s["display_name"] for s in response.json()["data"]]
        if len(names) > 1:
            assert names == sorted(names), "Systems should be sorted ascending by display_name"

    def test_v2_app_streams_systems_sort_order_desc(self, client, v2_prefix):
        """Verify sort_order=desc returns systems sorted descending."""
        _apply_auth_overrides(client)
        first = self._get_first_app_stream(client, v2_prefix)
        if first is None:
            pytest.skip("No app streams with systems found in test data")

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params=self._systems_params(first, limit=100, sort_order="desc"),
        )
        assert response.status_code == 200
        names = [s["display_name"] for s in response.json()["data"]]
        if len(names) > 1:
            assert names == sorted(names, reverse=True), "Systems should be sorted descending by display_name"

    def test_v2_app_streams_systems_sort_order_invalid(self, client, v2_prefix):
        """Verify invalid sort_order value is rejected by validation."""
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={"name": "test", "os_major": 9, "os_minor": 0, "sort_order": "invalid"},
        )
        assert response.status_code == 422
