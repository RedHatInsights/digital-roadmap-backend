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


class TestV2UpcomingRelevantWrapper:
    """Tests for the v2 Upcoming Changes relevant list wrapper endpoint."""

    def test_v2_upcoming_relevant_returns_empty_systems(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/upcoming-changes?all=true")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        for item in data:
            assert item["details"]["potentiallyAffectedSystems"] == [], (
                f"v2 should return empty potentiallyAffectedSystems for {item['name']}"
            )
            assert item["details"]["potentiallyAffectedSystemsDetail"] == [], (
                f"v2 should return empty potentiallyAffectedSystemsDetail for {item['name']}"
            )

    def test_v2_upcoming_relevant_counts_match_v1(self, client, v1_prefix, v2_prefix):
        _apply_auth_overrides(client)

        v1_response = client.get(f"{v1_prefix}/relevant/upcoming-changes?all=true")
        v2_response = client.get(f"{v2_prefix}/relevant/upcoming-changes?all=true")

        v1_data = v1_response.json()["data"]
        v2_data = v2_response.json()["data"]

        assert len(v1_data) == len(v2_data), "v1 and v2 should return the same number of items"

        v1_counts = {
            (item["name"], item["release"]): item["details"]["potentiallyAffectedSystemsCount"] for item in v1_data
        }
        v2_counts = {
            (item["name"], item["release"]): item["details"]["potentiallyAffectedSystemsCount"] for item in v2_data
        }

        assert v1_counts == v2_counts, "v1 and v2 counts must match for all items"

    def test_v2_upcoming_relevant_all_flag(self, client, v2_prefix):
        """Verify all=false (default) filtering works — items with zero systems excluded."""
        _apply_auth_overrides(client)

        response_default = client.get(f"{v2_prefix}/relevant/upcoming-changes")
        response_all = client.get(f"{v2_prefix}/relevant/upcoming-changes?all=true")

        data_default = response_default.json()["data"]
        data_all = response_all.json()["data"]

        assert response_default.status_code == 200
        assert response_all.status_code == 200

        # Default should have fewer or equal items compared to all=true
        assert len(data_default) <= len(data_all)

        # Default should only contain items with non-zero counts
        for item in data_default:
            assert item["details"]["potentiallyAffectedSystemsCount"] > 0, (
                f"Default filter should exclude items with 0 affected systems, but found {item['name']}"
            )

    def test_v2_upcoming_relevant_auth(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(f"{v2_prefix}/relevant/upcoming-changes")
        assert result.status_code == 403


class TestV2UpcomingSystems:
    """Tests for the v2 Upcoming Changes systems paginated endpoint."""

    def _get_first_upcoming_with_systems(self, client, v2_prefix):
        """Helper: fetch v2 list and return the first item with affected systems."""
        _apply_auth_overrides(client)
        response = client.get(f"{v2_prefix}/relevant/upcoming-changes")
        data = response.json()["data"]
        for item in data:
            if item["details"]["potentiallyAffectedSystemsCount"] > 0:
                return item
        return None

    def test_v2_upcoming_systems_basic(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_upcoming_with_systems(client, v2_prefix)
        if first is None:
            return

        response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": first["name"], "release": first["release"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "meta" in data
        assert "data" in data
        assert data["meta"]["count"] == len(data["data"])
        assert data["meta"]["count"] <= 10

    def test_v2_upcoming_systems_pagination(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_upcoming_with_systems(client, v2_prefix)
        if first is None:
            return

        params = {"name": first["name"], "release": first["release"]}

        page1 = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={**params, "offset": 0, "limit": 2},
        )
        page2 = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={**params, "offset": 2, "limit": 2},
        )

        assert page1.status_code == 200
        assert page2.status_code == 200
        assert page1.json()["meta"]["total"] == page2.json()["meta"]["total"]

        page1_ids = {s["id"] for s in page1.json()["data"]}
        page2_ids = {s["id"] for s in page2.json()["data"]}
        if page1_ids and page2_ids:
            assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"

    def test_v2_upcoming_systems_search(self, client, v2_prefix):
        _apply_auth_overrides(client)
        first = self._get_first_upcoming_with_systems(client, v2_prefix)
        if first is None:
            return

        all_response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": first["name"], "release": first["release"], "limit": 100},
        )

        all_data = all_response.json()["data"]
        if not all_data:
            return

        search_term = all_data[0]["display_name"][:5]
        search_response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={
                "name": first["name"],
                "release": first["release"],
                "search": search_term,
                "limit": 100,
            },
        )

        assert search_response.status_code == 200
        for system in search_response.json()["data"]:
            assert search_term.lower() in system["display_name"].lower()

    def test_v2_upcoming_systems_count_consistency(self, client, v2_prefix):
        """Verify list endpoint count matches systems endpoint total."""
        _apply_auth_overrides(client)
        first = self._get_first_upcoming_with_systems(client, v2_prefix)
        if first is None:
            return

        systems_response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": first["name"], "release": first["release"], "limit": 1},
        )

        assert systems_response.status_code == 200
        assert systems_response.json()["meta"]["total"] == first["details"]["potentiallyAffectedSystemsCount"], (
            f"List count ({first['details']['potentiallyAffectedSystemsCount']}) "
            f"does not match systems total ({systems_response.json()['meta']['total']}) "
            f"for {first['name']}"
        )

    def test_v2_upcoming_systems_not_found(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": "nonexistent-change-xyz", "release": "99.99"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []
        assert response.json()["meta"]["total"] == 0

    def test_v2_upcoming_systems_no_rbac_access(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": "test", "release": "9.0"},
        )
        assert result.status_code == 403

    def test_v2_upcoming_systems_limit_bounds(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": "test", "release": "9.0", "limit": 0},
        )
        assert response.status_code == 422

        response = client.get(
            f"{v2_prefix}/relevant/upcoming-changes/systems",
            params={"name": "test", "release": "9.0", "limit": 101},
        )
        assert response.status_code == 422
