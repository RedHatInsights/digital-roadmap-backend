"""Tests for notificator.__main__ — lifecycle notification orchestration and entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from notificator.__main__ import lifecycle_notification
from notificator.__main__ import main
from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION


class FakeNotificationProducer:
    """In-memory KafkaProducer stand-in that records sent payloads without I/O."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send_notification(self, payload: dict):
        self.sent.append(payload)


@asynccontextmanager
async def _fake_kafka_ctx(producer):
    yield producer


class TestLifecycleNotification:
    """lifecycle_notification: org iteration, payload dispatch, failure collection."""

    @pytest.fixture(autouse=True)
    def _setup(self, mocker):
        self.producer = FakeNotificationProducer()
        mocker.patch(
            "notificator.__main__.kafka_producer",
            side_effect=lambda: _fake_kafka_ctx(self.producer),
        )

    def _patch_notificator(self, mocker, org_ids, *, return_value=None, side_effect=None):
        """Patch get_org_ids and Notificator in one call; returns the class mock."""
        mocker.patch("notificator.__main__.get_org_ids", return_value=org_ids)
        mock_cls = mocker.patch("notificator.__main__.Notificator")
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

    async def test_single_org_failure_raises_runtime_error(self, mocker):
        """When the only org fails, RuntimeError is raised after the loop."""
        self._patch_notificator(mocker, [99], side_effect=ValueError("boom"))

        with pytest.raises(RuntimeError, match="1/1 orgs"):
            await lifecycle_notification()

    async def test_partial_failure_continues_remaining_orgs(self, mocker):
        """One org fails mid-batch; the rest still send their payloads."""
        self._patch_notificator(
            mocker,
            [1, 2, 3],
            side_effect=[{"seq": 1}, ValueError("org 2 failed"), {"seq": 3}],
        )

        with pytest.raises(RuntimeError, match=r"1/3 orgs: \[2\]"):
            await lifecycle_notification()

        assert len(self.producer.sent) == 2

    async def test_all_orgs_fail_reports_all(self, mocker):
        """When every org fails, all org IDs appear in the error message."""
        self._patch_notificator(mocker, [10, 20], side_effect=ValueError("fail"))

        with pytest.raises(RuntimeError, match=r"2/2 orgs: \[10, 20\]"):
            await lifecycle_notification()

        assert len(self.producer.sent) == 0

    async def test_notificator_receives_org_id(self, mocker):
        """Each Notificator is instantiated with the correct org_id."""
        mock_cls = self._patch_notificator(mocker, [777], return_value={})

        await lifecycle_notification()

        mock_cls.assert_called_once_with(org_id=777)

    async def test_no_subscribed_orgs_skips_processing(self, mocker):
        """When get_org_ids returns no orgs, skip without instantiating Notificator."""
        mock_cls = self._patch_notificator(mocker, [], return_value={})

        await lifecycle_notification()

        mock_cls.assert_not_called()
        assert len(self.producer.sent) == 0

    async def test_explicit_org_ids_forwarded_to_get_org_ids(self, mocker):
        """Passing org_ids forwards them to get_org_ids as a keyword argument."""
        get_mock = mocker.patch("notificator.__main__.get_org_ids", return_value=[42, 99])
        mock_cls = mocker.patch("notificator.__main__.Notificator")
        instance = AsyncMock()
        instance.get_lifecycle_notification.return_value = {"ok": True}
        mock_cls.return_value = instance

        await lifecycle_notification(org_ids=[42, 99])

        get_mock.assert_called_once_with(LIFECYCLE_SUBSCRIPTION, org_ids=[42, 99])
        assert len(self.producer.sent) == 2


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
