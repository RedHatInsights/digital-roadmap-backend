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

    async def test_single_org_failure_raises_runtime_error(self, mocker):
        """When the only org fails, RuntimeError is raised after the loop."""
        self._patch_notificator(mocker, [99], side_effect=ValueError("boom"))

        with pytest.raises(RuntimeError, match="1/1 orgs"):
            await roadmap_notification()

    async def test_partial_failure_continues_remaining_orgs(self, mocker):
        """One org fails mid-batch; the rest still send their payloads."""
        self._patch_notificator(
            mocker,
            [1, 2, 3],
            side_effect=[{"seq": 1}, ValueError("org 2 failed"), {"seq": 3}],
        )

        with pytest.raises(RuntimeError, match=r"1/3 orgs: \[2\]"):
            await roadmap_notification()

        assert len(self.producer.sent) == 2

    async def test_all_orgs_fail_reports_all(self, mocker):
        """When every org fails, all org IDs appear in the error message."""
        self._patch_notificator(mocker, [10, 20], side_effect=ValueError("fail"))

        with pytest.raises(RuntimeError, match=r"2/2 orgs: \[10, 20\]"):
            await roadmap_notification()

        assert len(self.producer.sent) == 0

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
