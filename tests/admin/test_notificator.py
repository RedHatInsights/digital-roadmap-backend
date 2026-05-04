"""Tests for the admin notificator trigger endpoint (PUT /api/roadmap/admin/notificator)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from notificator.kafka import KafkaBrokersNotConfigured


ADMIN_NOTIFICATOR_URL = "/api/roadmap/admin/notificator"


class FakeKafkaProducer:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_notification(self, payload: dict):
        self.sent.append(payload)


@asynccontextmanager
async def _fake_kafka_ctx(producer):
    yield producer


@pytest.fixture()
def fake_producer():
    return FakeKafkaProducer()


@pytest.fixture(autouse=True)
def _patch_kafka(mocker, fake_producer):
    mocker.patch(
        "roadmap.admin.notificator.kafka_producer",
        side_effect=lambda: _fake_kafka_ctx(fake_producer),
    )


@pytest.fixture(autouse=True)
def _patch_notificator(mocker):
    mock_cls = mocker.patch("roadmap.admin.notificator.Notificator")
    instance = AsyncMock()
    instance.get_lifecycle_notification.return_value = {"org_id": "42", "events": []}
    mock_cls.return_value = instance
    return mock_cls


class TestAdminAuth:
    """Tests for the admin notificator endpoint."""

    def test_missing_org_id_returns_422(self, client):
        response = client.put(ADMIN_NOTIFICATOR_URL)

        assert response.status_code == 422

    def test_invalid_org_id_returns_422(self, client):
        response = client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": "not-an-int"})

        assert response.status_code == 422


class TestTriggerNotificator:
    def test_success(self, client, fake_producer):
        response = client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": 42})

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Lifecycle notification sent for org 42"
        assert len(fake_producer.sent) == 1

    def test_notificator_passes_org_id(self, client, _patch_notificator):
        client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": 999})

        _patch_notificator.assert_called_once_with(org_id=999)

    def test_notificator_build_failure(self, client, mocker):
        mock_cls = mocker.patch("roadmap.admin.notificator.Notificator")
        instance = AsyncMock()
        instance.get_lifecycle_notification.side_effect = RuntimeError("db down")
        mock_cls.return_value = instance

        response = client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": 42})

        assert response.status_code == 500
        assert "Failed to build" in response.json()["detail"]

    def test_kafka_not_configured(self, client, mocker):
        mocker.patch(
            "roadmap.admin.notificator.kafka_producer",
            side_effect=KafkaBrokersNotConfigured("no brokers"),
        )

        response = client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": 42})

        assert response.status_code == 503
        assert "Kafka brokers not configured" in response.json()["detail"]

    def test_kafka_send_failure(self, client, mocker):
        failing_producer = AsyncMock()
        failing_producer.send_notification.side_effect = RuntimeError("kafka down")
        mocker.patch(
            "roadmap.admin.notificator.kafka_producer",
            side_effect=lambda: _fake_kafka_ctx(failing_producer),
        )

        response = client.put(ADMIN_NOTIFICATOR_URL, params={"org_id": 42})

        assert response.status_code == 500
        assert "Failed to send" in response.json()["detail"]
