from datetime import date
from unittest.mock import AsyncMock

import pytest

from notificator.notificator import _build_notification_payload
from roadmap.models import Meta
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle.rhel import RelevantSystemsResponse

from .utils import EMPTY_APPSTREAM_SECTIONS
from .utils import EMPTY_RHEL_SECTIONS
from .utils import FIXED_TIMESTAMP
from .utils import FIXED_UUID
from .utils import make_appstream_key
from .utils import make_system
from .utils import make_system_info
from .utils import ORG_ID


class TestNotificator:
    async def test_get_hosts(self, notificator):
        """Integration: fetching hosts from the test DB returns a non-empty list."""
        hosts = await notificator.get_hosts()

        assert isinstance(hosts, list)
        assert len(hosts) > 0

    async def test_get_hosts_no_db(self, notificator, mocker):
        """When no DB session is available, get_hosts returns an empty list."""

        async def _no_sessions():
            return
            yield  # noqa: unreachable — makes this an empty async generator

        mocker.patch("notificator.notificator.get_db", return_value=_no_sessions())

        hosts = await notificator.get_hosts()

        assert hosts == []

    async def test_get_relevant_appstreams(self, notificator, mocker):
        """Integration: result has both status sections, keys are 'rhel<N>', values have count & systems_count."""
        mock_date = mocker.patch("roadmap.data.app_streams.date", wraps=date)
        mock_date.today.return_value = date(2026, 4, 8)

        hosts = await notificator.get_hosts()
        result = await notificator.get_relevant_appstreams(hosts)

        assert "appstream_retired" in result
        assert "appstream_near_retirement" in result
        for section in result.values():
            for os_key, counts in section.items():
                assert os_key.startswith("rhel")
                assert "count" in counts
                assert "systems_count" in counts

    @pytest.mark.parametrize(
        ("systems_by_appstream", "expected"),
        (
            pytest.param(
                {},
                EMPTY_APPSTREAM_SECTIONS,
                id="empty",
            ),
            pytest.param(
                {
                    make_appstream_key("perl", "Perl 5.30", SupportStatus.supported, 8): {make_system_info(1, 8)},
                    make_appstream_key("ruby", "Ruby 2.7", SupportStatus.supported, 8): {make_system_info(2, 8)},
                },
                EMPTY_APPSTREAM_SECTIONS,
                id="two_rhel8_all_supported",
            ),
            pytest.param(
                {
                    make_appstream_key("postgres", "PostgreSQL 15", SupportStatus.retired, 9): {
                        make_system_info(1),
                        make_system_info(2),
                        make_system_info(3),
                    },
                },
                {
                    "appstream_retired": {"rhel9": {"count": 1, "systems_count": 3}},
                    "appstream_near_retirement": {"rhel9": {"count": 0, "systems_count": 0}},
                },
                id="one_rhel9_retired",
            ),
            pytest.param(
                {
                    make_appstream_key("postgres", "PostgreSQL 15", SupportStatus.retired, 9): {
                        make_system_info(1),
                        make_system_info(2),
                    },
                    make_appstream_key("httpd", "Apache HTTPD 2.4", SupportStatus.near_retirement, 9): {
                        make_system_info(3),
                    },
                },
                {
                    "appstream_retired": {"rhel9": {"count": 1, "systems_count": 2}},
                    "appstream_near_retirement": {"rhel9": {"count": 1, "systems_count": 1}},
                },
                id="one_retired_one_near_retirement",
            ),
            pytest.param(
                {
                    make_appstream_key("postgres", "PostgreSQL 12", SupportStatus.retired, 8): {make_system_info(1, 8)},
                    make_appstream_key("httpd", "Apache HTTPD 2.4", SupportStatus.near_retirement, 9): {
                        make_system_info(2),
                    },
                },
                {
                    "appstream_retired": {
                        "rhel8": {"count": 1, "systems_count": 1},
                        "rhel9": {"count": 0, "systems_count": 0},
                    },
                    "appstream_near_retirement": {
                        "rhel8": {"count": 0, "systems_count": 0},
                        "rhel9": {"count": 1, "systems_count": 1},
                    },
                },
                id="cross_os_major_backfill",
            ),
        ),
    )
    async def test_get_relevant_appstreams_scenarios(self, notificator, mocker, systems_by_appstream, expected):
        """Appstream grouping with mocked systems_by_app_stream.

        Scenarios (systems_by_appstream -> expected grouped output):
          empty                        - no appstreams → both sections empty
          two_rhel8_all_supported      - supported-only streams are filtered out
          one_rhel9_retired            - single retired stream, counts aggregated correctly
          one_retired_one_near_retirement - both statuses on the same os_major
          cross_os_major_backfill      - retired on RHEL 8, near-retirement on RHEL 9;
                                         verifies zero-count entries are back-filled across os_majors
        """
        mocker.patch(
            "notificator.notificator.systems_by_app_stream",
            new_callable=AsyncMock,
            return_value=systems_by_appstream,
        )

        result = await notificator.get_relevant_appstreams(hosts=[])

        assert result == expected

    async def test_get_relevant_rhel(self, notificator, mocker):
        """Integration: result has both status sections with rhel_versions_count & systems_count."""
        mock_date = mocker.patch("roadmap.models.date", wraps=date)
        mock_date.today.return_value = date(2026, 4, 8)

        hosts = await notificator.get_hosts()
        result = await notificator.get_relevant_rhel(hosts)

        assert "rhel_retired" in result
        assert "rhel_near_retirement" in result
        for section in result.values():
            assert "rhel_versions_count" in section
            assert "systems_count" in section

    @pytest.mark.parametrize(
        ("systems_data", "expected"),
        (
            pytest.param(
                [],
                EMPTY_RHEL_SECTIONS,
                id="empty",
            ),
            pytest.param(
                [make_system("RHEL", SupportStatus.retired, 5, 9, 1)],
                {
                    "rhel_retired": {"rhel_versions_count": 1, "systems_count": 5},
                    "rhel_near_retirement": {"rhel_versions_count": 0, "systems_count": 0},
                },
                id="single_retired",
            ),
            pytest.param(
                [
                    make_system("RHEL", SupportStatus.retired, 5, 8, 6),
                    make_system("RHEL", SupportStatus.near_retirement, 3, 9, 1),
                ],
                {
                    "rhel_retired": {"rhel_versions_count": 1, "systems_count": 5},
                    "rhel_near_retirement": {"rhel_versions_count": 1, "systems_count": 3},
                },
                id="mixed_retired_and_near_retirement",
            ),
            pytest.param(
                [make_system("CentOS", SupportStatus.retired, 10, 7, 0)],
                EMPTY_RHEL_SECTIONS,
                id="non_rhel_skipped",
            ),
            pytest.param(
                [make_system("RHEL", SupportStatus.supported, 8, 9, 4)],
                EMPTY_RHEL_SECTIONS,
                id="supported_filtered_out",
            ),
        ),
    )
    async def test_get_relevant_rhel_scenarios(self, notificator, mocker, systems_data, expected):
        """RHEL grouping with mocked get_relevant_systems.

        Scenarios (systems_data → expected grouped output):
          empty                        - no systems → both sections zeroed
          single_retired               - one retired RHEL version
          mixed_retired_and_near_retirement - one of each status, counts stay separate
          non_rhel_skipped             - CentOS is ignored, only RHEL counts
          supported_filtered_out       - supported status is not included in notification
        """
        response = RelevantSystemsResponse.model_construct(
            meta=Meta(count=len(systems_data), total=sum(s.count for s in systems_data)),
            data=systems_data,
        )
        mocker.patch(
            "notificator.notificator.get_relevant_systems",
            new_callable=AsyncMock,
            return_value=response,
        )

        result = await notificator.get_relevant_rhel(hosts=[])

        assert result == expected

    async def test_get_lifecycle_notification(self, notificator, mocker, mock_deterministic):
        """Orchestration: hosts are fetched once and passed to both rhel and appstream methods."""
        sentinel_hosts = [{"id": "sentinel"}]
        rhel = {
            "rhel_retired": {"rhel_versions_count": 2, "systems_count": 10},
            "rhel_near_retirement": {"rhel_versions_count": 1, "systems_count": 3},
        }
        appstreams = {
            "appstream_retired": {"rhel8": {"count": 2, "systems_count": 5}},
            "appstream_near_retirement": {},
        }
        mock_hosts = mocker.patch.object(notificator, "get_hosts", new_callable=AsyncMock, return_value=sentinel_hosts)
        mock_rhel = mocker.patch.object(notificator, "get_relevant_rhel", new_callable=AsyncMock, return_value=rhel)
        mock_apps = mocker.patch.object(
            notificator, "get_relevant_appstreams", new_callable=AsyncMock, return_value=appstreams
        )

        payload = await notificator.get_lifecycle_notification()

        mock_hosts.assert_awaited_once()
        mock_rhel.assert_awaited_once_with(sentinel_hosts)
        mock_apps.assert_awaited_once_with(sentinel_hosts)
        assert payload["event_type"] == "retiring-lifecycle-monthly-report"
        assert payload["org_id"] == str(ORG_ID)
        assert len(payload["events"]) == 1
        assert payload["events"][0]["payload"] == {**rhel, **appstreams}

    def test_build_notification_payload(self, mock_deterministic):
        """All fields of the Kafka notification payload match the expected schema."""
        rhel = {
            "rhel_retired": {"rhel_versions_count": 2, "systems_count": 10},
            "rhel_near_retirement": {"rhel_versions_count": 1, "systems_count": 3},
        }
        appstream = {
            "appstream_retired": {"rhel9": {"count": 3, "systems_count": 8}},
            "appstream_near_retirement": {"rhel9": {"count": 1, "systems_count": 2}},
        }

        result = _build_notification_payload(
            rhel_grouped=rhel,
            appstream_grouped=appstream,
            org_id=str(ORG_ID),
            event_type="retiring-lifecycle-monthly-report",
        )

        assert result["version"] == "v1.0.0"
        assert result["id"] == str(FIXED_UUID)
        assert result["bundle"] == "rhel"
        assert result["application"] == "planning"
        assert result["event_type"] == "retiring-lifecycle-monthly-report"
        assert result["timestamp"] == FIXED_TIMESTAMP
        assert result["org_id"] == str(ORG_ID)
        assert result["context"] == {}
        assert result["recipients"] == []
        assert len(result["events"]) == 1
        assert result["events"][0]["payload"] == {**rhel, **appstream}

    def test_build_notification_payload_empty_data(self, mock_deterministic):
        """With zeroed/empty inputs the payload still has the correct structure."""
        result = _build_notification_payload(
            rhel_grouped=EMPTY_RHEL_SECTIONS,
            appstream_grouped=EMPTY_APPSTREAM_SECTIONS,
            org_id=str(ORG_ID),
            event_type="retiring-lifecycle-monthly-report",
        )

        assert len(result["events"]) == 1
        assert result["events"][0]["payload"] == {**EMPTY_RHEL_SECTIONS, **EMPTY_APPSTREAM_SECTIONS}
        assert result["events"][0]["metadata"] == {}
