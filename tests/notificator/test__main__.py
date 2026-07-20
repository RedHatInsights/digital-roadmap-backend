"""Tests for notificator.__main__ — lifecycle notification orchestration and entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from notificator.__main__ import lifecycle_notification
from notificator.__main__ import main

from .utils import fake_kafka_ctx
from .utils import FakeNotificationProducer


class TestLifecycleNotification:
    """lifecycle_notification: org iteration, payload dispatch, failure collection."""

    @pytest.fixture(autouse=True)
    def _setup(self, mocker):
        self.producer = FakeNotificationProducer()
        mocker.patch(
            "notificator.lifecycle.kafka_producer",
            side_effect=lambda: fake_kafka_ctx(self.producer),
        )

    def _patch_notificator(self, mocker, org_ids, *, return_value=None, side_effect=None):
        """Patch get_org_ids and Notificator in one call; returns the class mock."""
        mocker.patch("notificator.lifecycle.get_org_ids", return_value=org_ids)
        mock_cls = mocker.patch("notificator.lifecycle.Notificator")
        instance = AsyncMock()
        if side_effect is not None:
            instance.get_lifecycle_notification.side_effect = side_effect
        elif return_value is not None:
            instance.get_lifecycle_notification.return_value = return_value
        mock_cls.return_value = instance
        return mock_cls

    async def test_single_org_sends_payload(self, mocker):
        """Happy path: one org produces a payload that reaches the producer."""
        payload = {"org_id": "42", "events": []}
        self._patch_notificator(mocker, [42], return_value=payload)

        await lifecycle_notification()

        assert self.producer.sent == [payload]

    async def test_multiple_orgs_all_succeed(self, mocker):
        """All orgs succeed — no error raised, each payload sent."""
        self._patch_notificator(mocker, [1, 2, 3], return_value={"ok": True})

        await lifecycle_notification()

        assert len(self.producer.sent) == 3

    async def test_single_org_failure_logs_error(self, mocker):
        """When the only org fails, the error is logged (no exception raised)."""
        self._patch_notificator(mocker, [99], side_effect=ValueError("boom"))
        log_error = mocker.patch("notificator.lifecycle.logger.error")

        await lifecycle_notification()

        log_error.assert_called_once_with(
            "Lifecycle notification failed for some orgs",
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
        log_error = mocker.patch("notificator.lifecycle.logger.error")

        await lifecycle_notification()

        assert len(self.producer.sent) == 2
        log_error.assert_called_once_with(
            "Lifecycle notification failed for some orgs",
            failed_orgs=[2],
            failed_count=1,
            total_count=3,
        )

    async def test_all_orgs_fail_reports_all(self, mocker):
        """When every org fails, all org IDs appear in the error log."""
        self._patch_notificator(mocker, [10, 20], side_effect=ValueError("fail"))
        log_error = mocker.patch("notificator.lifecycle.logger.error")

        await lifecycle_notification()

        assert len(self.producer.sent) == 0
        log_error.assert_called_once_with(
            "Lifecycle notification failed for some orgs",
            failed_orgs=[10, 20],
            failed_count=2,
            total_count=2,
        )

    async def test_notificator_receives_org_id(self, mocker):
        """Each Notificator is instantiated with the correct org_id."""
        mock_cls = self._patch_notificator(mocker, [777], return_value={})

        await lifecycle_notification()

        mock_cls.assert_called_once_with(org_id=777)

    async def test_get_org_ids_failure_returns_early(self, mocker):
        """When get_org_ids raises, the function logs and returns without processing."""
        mocker.patch(
            "notificator.lifecycle.get_org_ids",
            side_effect=RuntimeError("connection refused"),
        )
        log_exception = mocker.patch("notificator.lifecycle.logger.exception")

        await lifecycle_notification()

        log_exception.assert_called_once_with(
            "Failed to get org_ids for lifecycle notification, no orgs were notified."
        )
        assert len(self.producer.sent) == 0

    async def test_kafka_producer_failure_returns_early(self, mocker):
        """When kafka_producer raises, the function logs and returns without processing."""
        self._patch_notificator(mocker, [42], return_value={"ok": True})
        mocker.patch(
            "notificator.lifecycle.kafka_producer",
            side_effect=RuntimeError("broker unavailable"),
        )
        log_exception = mocker.patch("notificator.lifecycle.logger.exception")

        await lifecycle_notification()

        log_exception.assert_called_once_with(
            "Failed to initialize Kafka producer for lifecycle notification, no orgs were notified."
        )

    async def test_no_subscribed_orgs_skips_processing(self, mocker):
        """When get_org_ids returns no orgs, skip without instantiating Notificator."""
        mock_cls = self._patch_notificator(mocker, [], return_value={})

        await lifecycle_notification()

        mock_cls.assert_not_called()
        assert len(self.producer.sent) == 0

    async def test_explicit_org_ids_bypass_get_org_ids(self, mocker):
        """Passing org_ids skips get_org_ids entirely."""
        get_mock = mocker.patch("notificator.lifecycle.get_org_ids")
        mock_cls = mocker.patch("notificator.lifecycle.Notificator")
        instance = AsyncMock()
        instance.get_lifecycle_notification.return_value = {"ok": True}
        mock_cls.return_value = instance

        await lifecycle_notification(override_org_ids=[42, 99])

        get_mock.assert_not_called()
        assert len(self.producer.sent) == 2

    async def test_dry_run_generates_payload_but_skips_send(self, mocker):
        """In dry-run mode, payloads are generated but not sent to Kafka."""
        mock_cls = self._patch_notificator(mocker, [42, 99], return_value={"ok": True})
        send_spy = mocker.spy(self.producer, "send_notification")

        await lifecycle_notification(dry_run=True)

        assert mock_cls.call_count == 2
        send_spy.assert_not_called()


class TestMain:
    """main(): orchestrates both notification types in order."""

    async def test_calls_lifecycle_then_roadmap(self, mocker):
        """main() invokes lifecycle and then roadmap notification sequentially."""
        call_order = []

        async def fake_lifecycle():
            call_order.append("lifecycle")

        async def fake_roadmap():
            call_order.append("roadmap")

        mocker.patch("notificator.__main__.lifecycle_notification", side_effect=fake_lifecycle)
        mocker.patch("notificator.__main__.roadmap_notification", side_effect=fake_roadmap)

        await main()

        assert call_order == ["lifecycle", "roadmap"]
