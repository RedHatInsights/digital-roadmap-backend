from uuid import UUID
from datetime import date
from unittest.mock import MagicMock

import pytest

from fastapi import HTTPException

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream
from roadmap.common import query_host_inventory
from roadmap.data.app_streams import AppStreamEntity
from roadmap.data.app_streams import AppStreamImplementation
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle import app_streams
from roadmap.v2.relevant_app_streams import get_relevant_app_streams_v2
from roadmap.v2.relevant_app_streams import RelevantAppStreamV2
from roadmap.v2.relevant_app_streams import system_counts_by_app_stream
from tests.utils import SUPPORT_STATUS_TEST_CASES


@pytest.fixture
def inventory_result():
    def _result(rows):
        result = MagicMock()
        result.yield_per.return_value.mappings.return_value.__aiter__.return_value = rows
        return result

    return _result


def _apply_auth_overrides(client):
    async def get_allowed_host_groups_override():
        return set()

    async def decode_header_override():
        return "1234"

    client.app.dependency_overrides = {}
    client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
    client.app.dependency_overrides[decode_header] = decode_header_override


class TestV2AppStreamsRelevant:
    """Tests for the count-only v2 App Streams relevant list endpoint."""

    def test_v2_app_streams_relevant_omits_systems(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        for item in data:
            assert "systems" not in item
            assert "systems_detail" not in item

    @pytest.mark.parametrize("related", [False, True])
    @pytest.mark.parametrize("host_groups", [set(), {None}, {"aec18a86-3593-11f0-8426-5e43c8b8aa2f"}])
    def test_v2_app_streams_relevant_matches_v1(self, client, v1_prefix, v2_prefix, related, host_groups):
        _apply_auth_overrides(client)

        async def get_allowed_host_groups_override():
            return host_groups

        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override
        v1_response = client.get(f"{v1_prefix}/relevant/lifecycle/app-streams", params={"related": related})
        v2_response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams", params={"related": related})

        assert v1_response.status_code == v2_response.status_code == 200
        expected = v1_response.json()
        for item in expected["data"]:
            del item["systems"]
            del item["systems_detail"]

        assert v2_response.json() == expected

    def test_v2_app_streams_relevant_related(self, client, v2_prefix):
        _apply_auth_overrides(client)

        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams?related=true")
        data = response.json()["data"]

        assert response.status_code == 200
        assert len(data) > 0
        assert any(item["related"] for item in data)
        for item in data:
            assert "systems" not in item
            assert "systems_detail" not in item
            assert not item["rolling"]
            if item["related"]:
                assert item["count"] == 0
                assert item["support_status"] == SupportStatus.not_installed

    @pytest.mark.parametrize("related", [False, True])
    def test_empty_inventory(self, client, v2_prefix, inventory_result, related):
        """Related suggestions come from installed streams, so an empty inventory stays empty in both modes."""
        _apply_auth_overrides(client)

        async def query_override():
            return inventory_result([])

        client.app.dependency_overrides[query_host_inventory] = query_override
        response = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams", params={"related": related})

        assert response.status_code == 200
        assert response.json() == {"meta": {"count": 0, "total": 0}, "data": []}

    def test_openapi_omits_system_fields(self, client, v2_prefix):
        """The published list schema is counts only. Host lists live on the paginated systems endpoint."""
        schema = client.app.openapi()
        response_schema = schema["paths"][f"{v2_prefix}/relevant/lifecycle/app-streams"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        response_model = schema["components"]["schemas"][response_schema["$ref"].rsplit("/", 1)[1]]
        item_ref = response_model["properties"]["data"]["items"]["$ref"]
        item_model = schema["components"]["schemas"][item_ref.rsplit("/", 1)[1]]

        assert set(item_model["properties"]) == {
            "name",
            "application_stream_name",
            "application_stream_type",
            "display_name",
            "os_major",
            "os_minor",
            "start_date",
            "end_date",
            "count",
            "rolling",
            "support_status",
            "related",
        }

    def test_v2_app_streams_relevant_auth(self, client, v2_prefix):
        async def get_allowed_host_groups_override():
            raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

        client.app.dependency_overrides = {}
        client.app.dependency_overrides[get_allowed_host_groups] = get_allowed_host_groups_override

        result = client.get(f"{v2_prefix}/relevant/lifecycle/app-streams")
        assert result.status_code == 403


class TestAppStreamCounts:
    """Per-host stream counts, without keeping host records."""

    async def test_packages_count_once_per_host_without_host_details(self, inventory_result):
        """Several NEVRAs and architectures of one stream on a host count as one system; a second host counts again."""
        host = {
            "os_major": 9,
            "os_minor": 4,
            "dnf_modules": None,
            "packages": [
                "nodejs-1:16.20.2-8.el9_4.x86_64",
                "nodejs-1:16.20.2-8.el9_4.i686",
                "nodejs-1:16.14.0-5.el9.x86_64",
                "nodejs-1:16.14.0-5.el9.x86_64",
            ],
        }
        counts = await system_counts_by_app_stream("test-org", inventory_result([host, host.copy()]))

        assert {(key.name, key.app_stream_entity.os_major): count for key, count in counts.items()} == {
            ("Node.js 16", 9): 2
        }

    @pytest.mark.parametrize("packages_first", [False, True])
    async def test_module_package_overlap_preserves_module_name(self, inventory_result, monkeypatch, packages_first):
        """A module and its packages are one stream, kept under the module name.

        Related streams copy that name. It stays the module name whichever host is seen first.
        """
        entity = AppStreamEntity(
            name="nodejs",
            stream="16",
            application_stream_name="Node.js 16",
            os_major=9,
            start_date=date(2022, 5, 17),
            impl=AppStreamImplementation.module,
        )
        monkeypatch.setitem(app_streams.APP_STREAM_MODULES_BY_KEY, ("nodejs", 9, "16"), entity)
        package_key = app_streams.AppStreamKey(name="Node.js 16", app_stream_entity=entity)
        monkeypatch.setattr("roadmap.v2.relevant_app_streams.app_stream_from_package", lambda *args: package_key)
        host = {
            "os_major": 9,
            "os_minor": 4,
            "dnf_modules": [
                {"name": "nodejs", "stream": "16", "status": ["installed"]},
                {"name": "nodejs", "stream": "16", "status": ["installed"]},
            ],
            "packages": ["nodejs-1:16.20.2-8.el9_4.x86_64"],
        }
        hosts = [host, {**host, "dnf_modules": []}]
        if packages_first:
            hosts.reverse()

        counts = await system_counts_by_app_stream("test-org", inventory_result(hosts))

        assert [(key.name, count) for key, count in counts.items()] == [("nodejs", 2)]

    @pytest.mark.parametrize("packages_first", [False, True])
    async def test_related_streams_inherit_module_name(self, inventory_result, monkeypatch, packages_first):
        """A newer stream suggested from a module install keeps the module name and a zero count.

        Node.js 18 (module) and Node.js 16 (package) are one family, so Node.js 26
        appears once as nodejs / not installed, even when the package host is seen first.
        """
        candidate = AppStreamEntity(
            name="nodejs",
            stream="26",
            application_stream_name="Node.js 26",
            os_major=10,
            start_date=date(2026, 5, 1),
            end_date=date(2050, 5, 1),
            impl=AppStreamImplementation.package,
        )
        monkeypatch.setattr(app_streams, "APP_STREAM_MODULES_PACKAGES", [candidate])
        hosts = [
            {
                "os_major": 8,
                "os_minor": 10,
                "dnf_modules": [{"name": "nodejs", "stream": "18", "status": ["installed"]}],
                "packages": None,
            },
            {
                "os_major": 9,
                "os_minor": 4,
                "dnf_modules": None,
                "packages": ["nodejs-1:16.20.2-8.el9_4.x86_64"],
            },
        ]
        if packages_first:
            hosts.reverse()
        counts = await system_counts_by_app_stream("test-org", inventory_result(hosts))
        response = await get_relevant_app_streams_v2(counts, related=True)

        related = [item for item in response.data if item.related]
        assert [(item.name, item.application_stream_name, item.count) for item in related] == [
            ("nodejs", "Node.js 26", 0)
        ]
        assert related[0].support_status == SupportStatus.not_installed

    @pytest.mark.parametrize(
        "module, stream, status, packages, expected",
        [
            ("python36", "3.6", ["default"], [], False),  # RHEL 8 lists unused modules; default is not installed
            ("python36", "3.6", ["installed"], [], True),  # installed status counts without a package check
            ("python36", "3.6", ["enabled"], ["python36-3.6.8-1.el8.x86_64"], True),  # own package confirms it
            # enabled requires a matching package; bash does not belong to nodejs
            ("nodejs", "18", ["enabled", "installed"], ["bash-4.4.20-1.el8.x86_64"], False),
            ("scala", "2.10", ["enabled"], ["jansi-1.17.1-1.el8.noarch"], False),  # jansi is shared with maven
            # maven's own package confirms it; the shared jansi package does not
            ("maven", "3.5", ["enabled"], ["maven-3.5.4-1.el8.noarch", "jansi-1.17.1-1.el8.noarch"], True),
            ("php", "8.2", ["enabled", "installed"], ["php-cli-0:8.2.31-1.el8.x86_64"], True),  # php-cli matches php
        ],
    )
    async def test_module_verification(self, inventory_result, module, stream, status, packages, expected):
        """An enabled module counts only when that host's packages confirm the install.

        Installed status counts on its own. The extra host has no packages, so an enabled match does not carry over.
        """
        host = {
            "os_major": 8,
            "os_minor": 10,
            "dnf_modules": [{"name": module, "stream": stream, "status": status}],
            "packages": packages,
        }
        counts = await system_counts_by_app_stream("test-org", inventory_result([host, {**host, "packages": None}]))

        if expected:
            expected_count = 2 if status == ["installed"] else 1
            assert [(key.name, count) for key, count in counts.items()] == [(module, expected_count)]
        else:
            assert counts == {}

    async def test_enabled_module_without_package_mapping(self, inventory_result, monkeypatch):
        """Skip an enabled module when there is no package list to confirm it with."""
        monkeypatch.setattr(app_streams, "MODULE_PACKAGES", {})
        host = {
            "os_major": 8,
            "os_minor": 10,
            "dnf_modules": [{"name": "python36", "stream": "3.6", "status": ["enabled"]}],
            "packages": ["python36-3.6.8-1.el8.x86_64"],
        }
        assert await system_counts_by_app_stream("test-org", inventory_result([host])) == {}

    async def test_missing_inventory_data(self, inventory_result):
        """Skip hosts with no RHEL version. A host identified only by os_release still counts."""
        hosts = [
            {"dnf_modules": None, "packages": None},
            {"os_major": 8, "os_minor": 10, "dnf_modules": None, "packages": None},
            {
                "os_release": "9.4",
                "dnf_modules": None,
                "packages": ["nodejs-1:16.20.2-8.el9_4.x86_64"],
            },
        ]
        counts = await system_counts_by_app_stream("test-org", inventory_result(hosts))
        assert [(key.name, count) for key, count in counts.items()] == [("Node.js 16", 1)]

    async def test_rolling_streams_excluded(self, inventory_result):
        """Rolling streams such as container-tools are detected, then omitted from the list, same as v1."""
        host = {
            "os_major": 8,
            "os_minor": 10,
            "dnf_modules": [{"name": "container-tools", "stream": "rhel8", "status": ["enabled"]}],
            "packages": ["podman-4.9.4-1.el8.x86_64", "buildah-1.33.7-1.el8.x86_64"],
        }
        counts = await system_counts_by_app_stream("test-org", inventory_result([host]))
        assert [(key.name, count) for key, count in counts.items()] == [("container-tools", 1)]

        response = await get_relevant_app_streams_v2(counts)
        assert response.model_dump() == {"meta": {"count": 0, "total": 0}, "data": []}


@pytest.mark.parametrize(
    "current_date, start_date, end_date, expected_status",
    SUPPORT_STATUS_TEST_CASES
    # Ends within six months: app streams are near retirement inside that window.
    + ((date(2027, 6, 15), date(2020, 1, 1), date(2027, 12, 1), SupportStatus.near_retirement),),
)
def test_v2_support_status(mocker, current_date, start_date, end_date, expected_status):
    """Installed v2 streams use the shared support-status dates, including the six-month near-retirement window."""
    mock_date = mocker.patch("roadmap.v2.relevant_app_streams.date", wraps=date)
    mock_date.today.return_value = current_date
    stream = RelevantAppStreamV2(
        name="test",
        application_stream_name="Test 1",
        display_name="Test 1",
        os_major=9,
        start_date=start_date,
        end_date=end_date,
        count=1,
    )

    assert stream.support_status == expected_status


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

    def test_v2_app_streams_systems_exact_match_precedence(self, client, v2_prefix):
        """Verify exact os_minor match takes precedence over wildcard.

        When both a wildcard (os_minor=None) and exact match (os_minor=<value>)
        exist for the same name+os_major, querying with the specific minor version
        should return systems from the exact match, not the wildcard.
        """
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
        wildcard_key = AppStreamKey(name="controlled-stream", app_stream_entity=wildcard_entity)
        exact_key = AppStreamKey(name="controlled-stream", app_stream_entity=exact_entity)
        wildcard_systems = {SystemInfo(id=UUID(int=3), display_name="Wildcard host", os_major=9, os_minor=0)}
        exact_systems = {
            SystemInfo(id=UUID(int=1), display_name="Exact host 1", os_major=9, os_minor=1),
            SystemInfo(id=UUID(int=2), display_name="Exact host 2", os_major=9, os_minor=1),
        }

        async def controlled_systems_by_app_stream():
            return {wildcard_key: wildcard_systems, exact_key: exact_systems}

        client.app.dependency_overrides[systems_by_app_stream] = controlled_systems_by_app_stream

        r = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={
                "name": "controlled-stream",
                "os_major": 9,
                "os_minor": 1,
            },
        )
        assert r.status_code == 200
        response = r.json()
        returned_ids = {system["id"] for system in response["data"]}
        exact_ids = {str(system.id) for system in exact_systems}
        assert response["meta"]["total"] == len(exact_ids)
        assert returned_ids == exact_ids

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

        # Case 2: send a minor version that definitely doesn't exist for this stream
        # Find all existing minor versions for this stream
        existing_minors = set()
        for item in data:
            if (
                item.get("name") == target["name"]
                and item.get("os_major") == target["os_major"]
                and item.get("os_minor") is not None
            ):
                existing_minors.add(item["os_minor"])

        # Select a minor version that doesn't exist
        nonexistent_minor = 0
        while nonexistent_minor in existing_minors:
            nonexistent_minor += 1

        r2 = client.get(
            f"{v2_prefix}/relevant/lifecycle/app-streams/systems",
            params={
                "name": target["name"],
                "os_major": target["os_major"],
                "os_minor": nonexistent_minor,
                "limit": 1,
            },
        )
        assert r2.status_code == 200
        assert r2.json()["meta"]["total"] == target["count"], (
            f"Sending os_minor={nonexistent_minor} (no exact match) should fallback to "
            f"os_minor=None entity, expected {target['count']} but got {r2.json()['meta']['total']}"
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
