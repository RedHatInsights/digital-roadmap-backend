"""Tests for notificator.roadmap — roadmap notification orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from notificator.roadmap import roadmap_notification

from .utils import fake_kafka_ctx
from .utils import FakeNotificationProducer


class TestRoadmapNotification:
    """roadmap_notification: org iteration, payload dispatch, failure collection."""

    @pytest.fixture(autouse=True)
    def _setup(self, mocker):
        self.producer = FakeNotificationProducer()
        mocker.patch(
            "notificator.roadmap.kafka_producer",
            side_effect=lambda: fake_kafka_ctx(self.producer),
        )

    def _patch_notificator(self, mocker, org_ids, *, return_value=None, side_effect=None):
        """Patch get_org_ids and Notificator in one call; returns (cls_mock, get_org_ids_mock)."""
        get_mock = mocker.patch("notificator.roadmap.get_org_ids", new_callable=AsyncMock, return_value=org_ids)
        mock_cls = mocker.patch("notificator.roadmap.Notificator")
        instance = AsyncMock()
        if side_effect is not None:
            instance.get_roadmap_notification.side_effect = side_effect
        elif return_value is not None:
            instance.get_roadmap_notification.return_value = return_value
        mock_cls.return_value = instance
        return mock_cls, get_mock

    async def test_single_org_sends_payload(self, mocker):
        """Happy path: one org produces a payload that reaches the producer."""
        payload = {"org_id": "42", "events": []}
        self._patch_notificator(mocker, [42], return_value=payload)

        await roadmap_notification()

        assert self.producer.sent == [payload]

    async def test_multiple_orgs_all_succeed(self, mocker):
        """All orgs succeed — no error raised, each payload sent."""
        self._patch_notificator(mocker, [1, 2, 3], return_value={"ok": True})

        await roadmap_notification()

        assert len(self.producer.sent) == 3

    async def test_single_org_failure_logs_error(self, mocker):
        """When the only org fails, the error is logged (no exception raised)."""
        self._patch_notificator(mocker, [99], side_effect=ValueError("boom"))
        log_error = mocker.patch("notificator.roadmap.logger.error")

        await roadmap_notification()

        log_error.assert_called_once_with(
            "Roadmap notification failed for some orgs",
            failed_orgs=[99],
            failed_count=1,
            total_count=1,
        )

    async def test_partial_failure_continues_remaining_orgs(self, mocker):
        """One org fails mid-batch; the rest still send their payloads."""
        self._patch_notificator(
            mocker,
            [1, 2, 3],
            side_effect=[{"seq": 1}, ValueError("org 2 failed"), {"seq": 3}],
        )
        log_error = mocker.patch("notificator.roadmap.logger.error")

        await roadmap_notification()

        assert len(self.producer.sent) == 2
        log_error.assert_called_once_with(
            "Roadmap notification failed for some orgs",
            failed_orgs=[2],
            failed_count=1,
            total_count=3,
        )

    async def test_all_orgs_fail_reports_all(self, mocker):
        """When every org fails, all org IDs appear in the error log."""
        self._patch_notificator(mocker, [10, 20], side_effect=ValueError("fail"))
        log_error = mocker.patch("notificator.roadmap.logger.error")

        await roadmap_notification()

        assert len(self.producer.sent) == 0
        log_error.assert_called_once_with(
            "Roadmap notification failed for some orgs",
            failed_orgs=[10, 20],
            failed_count=2,
            total_count=2,
        )

    async def test_get_org_ids_failure_returns_early(self, mocker):
        """When get_org_ids raises, the function logs and returns without processing."""
        mocker.patch(
            "notificator.roadmap.get_org_ids",
            side_effect=RuntimeError("connection refused"),
        )
        log_exception = mocker.patch("notificator.roadmap.logger.exception")

        await roadmap_notification()

        log_exception.assert_called_once_with("Failed to get org_ids for roadmap notification, no orgs were notified.")
        assert len(self.producer.sent) == 0

    async def test_kafka_producer_failure_returns_early(self, mocker):
        """When kafka_producer raises, the function logs and returns without processing."""
        self._patch_notificator(mocker, [42], return_value={"ok": True})
        mocker.patch(
            "notificator.roadmap.kafka_producer",
            side_effect=RuntimeError("broker unavailable"),
        )
        log_exception = mocker.patch("notificator.roadmap.logger.exception")

        await roadmap_notification()

        log_exception.assert_called_once_with(
            "Failed to get kafka producer for roadmap notification, no orgs were notified."
        )

    async def test_no_subscribed_orgs_skips_processing(self, mocker):
        """When get_org_ids returns no orgs, skip without instantiating Notificator."""
        mock_cls, _ = self._patch_notificator(mocker, [], return_value={})

        await roadmap_notification()

        mock_cls.assert_not_called()
        assert len(self.producer.sent) == 0

    async def test_explicit_org_ids_bypass_get_org_ids(self, mocker):
        """Passing org_ids skips get_org_ids entirely."""
        _, get_mock = self._patch_notificator(mocker, [], return_value={"ok": True})

        await roadmap_notification(override_org_ids=[42, 99])

        get_mock.assert_not_called()
        assert len(self.producer.sent) == 2
