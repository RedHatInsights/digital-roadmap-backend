"""Tests for the admin notificator trigger endpoint (PUT /api/roadmap/admin/notificator)."""

from __future__ import annotations

import base64
import json

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from notificator.kafka import KafkaBrokersNotConfigured


ADMIN_NOTIFICATOR_URL = "/api/roadmap/admin/notificator"


def _make_identity_header(org_id: str, identity_type: str = "Associate", email: str = "admin@redhat.com") -> str:
    payload = {
        "identity": {
            "org_id": org_id,
            "type": identity_type,
            "associate": {"email": email},
        }
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


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
    """Tests for the require_associate auth dependency on admin routes."""

    def test_missing_identity_header_returns_401(self, client):
        response = client.put(ADMIN_NOTIFICATOR_URL)

        assert response.status_code == 401
        assert "Missing x-rh-identity" in response.json()["detail"]

    def test_non_associate_identity_returns_401(self, client):
        headers = {"x-rh-identity": _make_identity_header("42", identity_type="User")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 401
        assert "associate identity" in response.json()["detail"]

    def test_invalid_base64_returns_401(self, client):
        headers = {"x-rh-identity": "not-valid-base64!!!"}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 401

    def test_invalid_json_returns_401(self, client):
        headers = {"x-rh-identity": base64.b64encode(b"not json").decode()}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 401

    def test_empty_identity_type_returns_401(self, client):
        headers = {"x-rh-identity": _make_identity_header("42", identity_type="")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 401

    def test_associate_type_case_insensitive(self, client, fake_producer):
        headers = {"x-rh-identity": _make_identity_header("42", identity_type="associate")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 200


class TestTriggerNotificator:
    def test_success(self, client, fake_producer):
        headers = {"x-rh-identity": _make_identity_header("42")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Lifecycle notification sent for org 42"
        assert len(fake_producer.sent) == 1

    def test_missing_org_id_in_identity(self, client):
        headers = {"x-rh-identity": _make_identity_header("", identity_type="Associate")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 400
        assert "Missing org_id" in response.json()["detail"]

    def test_notificator_passes_org_id(self, client, _patch_notificator):
        headers = {"x-rh-identity": _make_identity_header("999")}
        client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        _patch_notificator.assert_called_once_with(org_id=999)

    def test_notificator_build_failure(self, client, mocker):
        mock_cls = mocker.patch("roadmap.admin.notificator.Notificator")
        instance = AsyncMock()
        instance.get_lifecycle_notification.side_effect = RuntimeError("db down")
        mock_cls.return_value = instance

        headers = {"x-rh-identity": _make_identity_header("42")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 500
        assert "Failed to build" in response.json()["detail"]

    def test_kafka_not_configured(self, client, mocker):
        mocker.patch(
            "roadmap.admin.notificator.kafka_producer",
            side_effect=KafkaBrokersNotConfigured("no brokers"),
        )

        headers = {"x-rh-identity": _make_identity_header("42")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 503
        assert "Kafka brokers not configured" in response.json()["detail"]

    def test_kafka_send_failure(self, client, mocker):
        failing_producer = AsyncMock()
        failing_producer.send_notification.side_effect = RuntimeError("kafka down")
        mocker.patch(
            "roadmap.admin.notificator.kafka_producer",
            side_effect=lambda: _fake_kafka_ctx(failing_producer),
        )

        headers = {"x-rh-identity": _make_identity_header("42")}
        response = client.put(ADMIN_NOTIFICATOR_URL, headers=headers)

        assert response.status_code == 500
        assert "Failed to send" in response.json()["detail"]
