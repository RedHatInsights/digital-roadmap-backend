import uuid

from unittest.mock import AsyncMock

import pytest

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

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


class TestV2RhelRelevantWrapper:
    """Tests for the v2 RHEL relevant list wrapper endpoint."""

    def test_v2_rhel_relevant_returns_empty_systems(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        for item in data:
            assert item["systems"] == [], f"v2 should return empty systems for {item}"
            assert item["systems_detail"] == [], f"v2 should return empty systems_detail for {item}"

    def test_v2_rhel_relevant_counts_match_v1(self, client, v1_prefix, v2_prefix):
        _apply_auth_overrides(client)

        v1_response = client.get(f"{v1_prefix}/relevant/lifecycle/rhel")
        v2_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")

        v1_data = v1_response.json()["data"]
        v2_data = v2_response.json()["data"]

        assert len(v1_data) == len(v2_data), "v1 and v2 should return the same number of items"

        v1_counts = {(item["major"], item["minor"], item["lifecycle_type"]): item["count"] for item in v1_data}
        v2_counts = {(item["major"], item["minor"], item["lifecycle_type"]): item["count"] for item in v2_data}

        assert v1_counts == v2_counts, "v1 and v2 counts must match for all items"

    def test_v2_rhel_relevant_related(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel?related=true")
        data = response.json()["data"]
        related_hosts = [item for item in data if not item["count"]]

        assert response.status_code == 200
        assert len(data) > 1
        assert len(related_hosts) > 0
        for item in data:
            assert item["systems"] == []
            assert item["systems_detail"] == []

    def test_v2_rhel_relevant_auth(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")
        assert result.status_code == 403

    def test_v2_rhel_relevant_meta_total(self, client, v1_prefix, v2_prefix):
        _apply_auth_overrides(client)

        v1_response = client.get(f"{v1_prefix}/relevant/lifecycle/rhel")
        v2_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")

        v1_meta = v1_response.json()["meta"]
        v2_meta = v2_response.json()["meta"]

        assert v1_meta["count"] == v2_meta["count"]
        assert v1_meta["total"] == v2_meta["total"]


class TestV2RhelSystems:
    """Tests for the v2 RHEL systems paginated endpoint.

    Note: The RHEL systems endpoint uses a SQL query against hbi.hosts which
    requires a running Postgres database with loaded test data. In the test
    environment, this database is set up via `make start-db load-host-data`.
    Tests that require the database use the `requires_db` fixture which probes
    the connection once per session and skips when unavailable.
    """

    def _get_first_rhel_with_systems(self, client, v2_prefix):
        """Helper: fetch v2 RHEL list and return the first item with count > 0."""
        _apply_auth_overrides(client)
        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")
        data = response.json()["data"]
        for item in data:
            if item["count"] > 0:
                return item
        return None

    def test_v2_rhel_systems_count_consistency(self, client, v2_prefix, requires_db):
        """Verify list endpoint count matches systems endpoint total for each version.

        This is the critical data consistency test: the v2 list wrapper uses
        Python-level logic (via v1) while the /systems endpoint uses a
        dedicated SQL query. Any divergence in filtering logic will surface
        as a count mismatch here.
        """
        _apply_auth_overrides(client)
        first = self._get_first_rhel_with_systems(client, v2_prefix)
        if first is None:
            pytest.skip("No RHEL versions with systems found in test data")

        major, minor = first["major"], first["minor"]
        lifecycle_type = first["lifecycle_type"]
        list_count = first["count"]

        systems_response = client.get(
            f"{v2_prefix}/relevant/lifecycle/rhel/{major}/{minor}/systems",
            params={"lifecycle_type": lifecycle_type, "limit": 1},
        )

        assert systems_response.status_code == 200
        systems_total = systems_response.json()["meta"]["total"]
        assert systems_total == list_count, (
            f"List count ({list_count}) does not match systems total "
            f"({systems_total}) for RHEL {major}.{minor} [{lifecycle_type}]"
        )

    def test_v2_rhel_systems_count_consistency_all_versions(self, client, v2_prefix, requires_db):
        """Verify count consistency across ALL RHEL versions, not just the first."""
        _apply_auth_overrides(client)

        v2_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")
        v2_data = v2_response.json()["data"]

        checked = 0
        for item in v2_data:
            if item["count"] == 0:
                continue

            major, minor = item["major"], item["minor"]
            lifecycle_type = item["lifecycle_type"]
            list_count = item["count"]

            if not (7 <= major <= 10 and 0 <= minor <= 10):
                continue

            systems_response = client.get(
                f"{v2_prefix}/relevant/lifecycle/rhel/{major}/{minor}/systems",
                params={"lifecycle_type": lifecycle_type, "limit": 1},
            )

            assert systems_response.status_code == 200
            systems_total = systems_response.json()["meta"]["total"]
            assert systems_total == list_count, (
                f"List count ({list_count}) does not match systems total "
                f"({systems_total}) for RHEL {major}.{minor} [{lifecycle_type}]"
            )
            checked += 1

        assert checked > 0, "Expected at least one RHEL version with systems to check"

    def test_v2_rhel_systems_empty_result(self, client, v2_prefix, requires_db):
        """Call with a version that has no hosts — should return empty result."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/7/0/systems")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0
        assert data["meta"]["count"] == 0

    def test_v2_rhel_systems_limit_bounds(self, client, v2_prefix):
        """Verify limit max 100 and min 1 are enforced by validation."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=0")
        assert response.status_code == 422

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=101")
        assert response.status_code == 422

    def test_v2_rhel_systems_offset_bounds(self, client, v2_prefix):
        """Verify offset min 0 is enforced by validation."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?offset=-1")
        assert response.status_code == 422

    def test_v2_rhel_systems_no_rbac_access(self, client, v2_prefix):
        """Assert 403 when RBAC denies access."""

        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems")
        assert result.status_code == 403

    def test_v2_rhel_systems_basic(self, client, v2_prefix, ids_by_os, requires_db):
        """Call with a known version. Verify response structure and content."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems")

        assert response.status_code == 200
        data = response.json()
        assert "meta" in data
        assert "data" in data
        assert data["meta"]["count"] <= 10, "Default limit is 10"
        assert data["meta"]["count"] == len(data["data"])

        for system in data["data"]:
            assert "id" in system
            assert "display_name" in system
            assert "os_major" in system
            assert "os_minor" in system
            assert uuid.UUID(system["id"]), "System ID should be a valid UUID"

    def test_v2_rhel_systems_pagination(self, client, v2_prefix, requires_db):
        """Call with small limit, then offset — verify different pages."""
        _apply_auth_overrides(client)

        page1 = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?offset=0&limit=2")
        page2 = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?offset=2&limit=2")

        assert page1.status_code == 200
        assert page2.status_code == 200

        page1_ids = {s["id"] for s in page1.json()["data"]}
        page2_ids = {s["id"] for s in page2.json()["data"]}

        assert page1.json()["meta"]["total"] == page2.json()["meta"]["total"], "Total should be consistent"

        if page1_ids and page2_ids:
            assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"

    def test_v2_rhel_systems_search(self, client, v2_prefix, requires_db):
        """Call with a search filter — verify only matching systems are returned."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=100")

        assert response.status_code == 200
        all_data = response.json()["data"]

        if not all_data:
            pytest.skip("No RHEL 9.1 systems in test data to test search")

        search_term = all_data[0]["display_name"][:5]
        search_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?search={search_term}&limit=100")

        assert search_response.status_code == 200
        for system in search_response.json()["data"]:
            assert search_term.lower() in system["display_name"].lower()

    def test_v2_rhel_systems_lifecycle_type_filter(self, client, v2_prefix, requires_db):
        """Call with lifecycle_type=EUS — verify only that type's systems are returned."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/2/systems?lifecycle_type=EUS")

        assert response.status_code == 200

    def test_v2_rhel_systems_os_release_fallback(self, client, v2_prefix, requires_db):
        """Verify hosts with os_name but no major/minor (only os_release) are included.

        The test fixture contains a host with operating_system={'name': 'RHEL'}
        and os_release='9.6' but no major/minor keys. The SQL query must fall
        back to os_release for version extraction. This edge case was the root
        cause of a count inconsistency bug between the v1 Python logic and v2
        SQL query.
        """
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/6/systems?limit=100")

        assert response.status_code == 200
        systems_total = response.json()["meta"]["total"]

        v2_list = client.get(f"{v2_prefix}/relevant/lifecycle/rhel")
        list_data = v2_list.json()["data"]
        list_count_96 = 0
        for item in list_data:
            if item["major"] == 9 and item["minor"] == 6:
                list_count_96 += item["count"]

        assert systems_total == list_count_96, (
            f"RHEL 9.6 systems total ({systems_total}) does not match "
            f"list count ({list_count_96}). This likely means the SQL query "
            f"is not correctly falling back to os_release for hosts with "
            f"incomplete operating_system JSONB data."
        )

    def test_v2_rhel_systems_excludes_null_os_name(self, client, v2_prefix, requires_db):
        """Verify hosts with empty operating_system dict (os_name=None) are excluded.

        The test fixture has a host with operating_system={} and os_release='9.6'.
        Both v1 Python logic and v2 SQL query should exclude this host because
        os_name is null/missing.
        """
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/6/systems?limit=100")

        assert response.status_code == 200
        system_ids = {s["id"] for s in response.json()["data"]}

        assert "96e0810e-1fc6-496f-ba52-a609a382ee86" not in system_ids, (
            "Host with empty operating_system dict (no os_name) should be excluded from RHEL systems query"
        )

    def test_v2_rhel_systems_db_error_returns_500(self, client, v2_prefix):
        """Verify the endpoint returns HTTP 500 when a database error occurs."""
        _apply_auth_overrides(client)

        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("connection refused")

        async def get_db_override():
            yield mock_session

        from roadmap.database import get_db

        client.app.dependency_overrides[get_db] = get_db_override

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems")

        assert response.status_code == 500
        assert response.json()["detail"] == "Error querying host inventory"

        del client.app.dependency_overrides[get_db]

    def test_v2_rhel_systems_major_out_of_range(self, client, v2_prefix):
        """Verify major version path parameter rejects values outside 7-10."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/6/0/systems")
        assert response.status_code == 422

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/11/0/systems")
        assert response.status_code == 422

    def test_v2_rhel_systems_minor_out_of_range(self, client, v2_prefix):
        """Verify minor version path parameter rejects values outside 0-10."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/-1/systems")
        assert response.status_code == 422

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/11/systems")
        assert response.status_code == 422

    def test_v2_rhel_systems_sort_order_asc(self, client, v2_prefix, requires_db):
        """Verify sort_order=asc returns systems sorted by display_name ascending."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=100&sort_order=asc")
        assert response.status_code == 200
        names = [s["display_name"] for s in response.json()["data"]]
        if len(names) > 1:
            assert names == sorted(names), "Systems should be sorted ascending by display_name"

    def test_v2_rhel_systems_sort_order_desc(self, client, v2_prefix, requires_db):
        """Verify sort_order=desc returns systems sorted by display_name descending."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=100&sort_order=desc")
        assert response.status_code == 200
        names = [s["display_name"] for s in response.json()["data"]]
        if len(names) > 1:
            assert names == sorted(names, reverse=True), "Systems should be sorted descending by display_name"

    def test_v2_rhel_systems_sort_order_default_is_asc(self, client, v2_prefix, requires_db):
        """Verify default sort order (no param) matches explicit asc."""
        _apply_auth_overrides(client)

        default_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=100")
        asc_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=100&sort_order=asc")

        assert default_response.status_code == 200
        assert asc_response.status_code == 200
        assert default_response.json()["data"] == asc_response.json()["data"]

    def test_v2_rhel_systems_sort_order_invalid(self, client, v2_prefix):
        """Verify invalid sort_order value is rejected by validation."""
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?sort_order=invalid")
        assert response.status_code == 422

    def test_v2_rhel_systems_sort_order_reverses_results(self, client, v2_prefix, requires_db):
        """Verify asc and desc return opposite orderings."""
        _apply_auth_overrides(client)

        asc_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=5&sort_order=asc")
        desc_response = client.get(f"{v2_prefix}/relevant/lifecycle/rhel/9/1/systems?limit=5&sort_order=desc")

        assert asc_response.status_code == 200
        assert desc_response.status_code == 200

        assert asc_response.json()["meta"]["total"] == desc_response.json()["meta"]["total"]

        asc_names = [s["display_name"] for s in asc_response.json()["data"]]
        desc_names = [s["display_name"] for s in desc_response.json()["data"]]
        if asc_names and desc_names:
            assert asc_names[0] <= desc_names[0], "ASC first item should be <= DESC first item"
            assert desc_names[0] >= asc_names[0], "DESC first item should be >= ASC first item"
