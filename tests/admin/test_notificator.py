"""Tests for admin notificator endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from notificator.kafka import KafkaBrokersNotConfigured


ADMIN_NOTIFICATOR_CUSTOM_URL = "/api/roadmap/admin/notificator/custom"
ADMIN_NOTIFICATOR_ALL_URL = "/api/roadmap/admin/notificator/all"


@pytest.fixture(autouse=True)
def _patch_lifecycle_notification(mocker):
    return mocker.patch("roadmap.admin.notificator.lifecycle_notification", new_callable=AsyncMock)


class TestCustomEndpointValidation:
    """Validation tests for custom endpoint."""

    def test_missing_body_returns_422(self, client):
        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL)

        assert response.status_code == 422

    def test_invalid_org_ids_type_returns_422(self, client):
        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": "not-an-int"})

        assert response.status_code == 422

    def test_empty_org_ids_returns_422(self, client):
        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": []})

        assert response.status_code == 422


class TestTriggerNotificator:
    def test_custom_success_single_org(self, client, _patch_lifecycle_notification):
        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": 42})

        assert response.status_code == 200
        body = response.json()
        assert body == {"message": "Lifecycle notification completed", "requested_org_ids": [42]}
        _patch_lifecycle_notification.assert_awaited_once_with(override_org_ids=[42])

    def test_custom_deduplicates_and_sorts_org_ids(self, client, _patch_lifecycle_notification):
        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": [3, 1, 3, 2]})

        assert response.status_code == 200
        assert response.json()["requested_org_ids"] == [1, 2, 3]
        _patch_lifecycle_notification.assert_awaited_once_with(override_org_ids=[1, 2, 3])

    def test_custom_runtime_failure(self, client, _patch_lifecycle_notification):
        _patch_lifecycle_notification.side_effect = RuntimeError("failed for 1/1 orgs")

        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": 42})

        assert response.status_code == 500
        assert "failed for 1/1 orgs" in response.json()["detail"]

    def test_custom_kafka_not_configured(self, client, _patch_lifecycle_notification):
        _patch_lifecycle_notification.side_effect = KafkaBrokersNotConfigured("no brokers")

        response = client.post(ADMIN_NOTIFICATOR_CUSTOM_URL, json={"org_ids": 42})

        assert response.status_code == 503
        assert "Kafka brokers not configured" in response.json()["detail"]

    def test_all_requires_confirmation(self, client):
        response = client.post(ADMIN_NOTIFICATOR_ALL_URL, json={"confirm_all": False})

        assert response.status_code == 400
        assert "confirm_all=true" in response.json()["detail"]

    def test_all_accepts_and_triggers_background(self, client, _patch_lifecycle_notification):
        response = client.post(ADMIN_NOTIFICATOR_ALL_URL, json={"confirm_all": True})

        assert response.status_code == 202
        assert response.json() == {"message": "Lifecycle notification accepted"}
        _patch_lifecycle_notification.assert_awaited_once_with(override_org_ids=None)

    def test_all_background_failure_still_returns_202(self, client, _patch_lifecycle_notification):
        _patch_lifecycle_notification.side_effect = RuntimeError("batch failed")

        response = client.post(ADMIN_NOTIFICATOR_ALL_URL, json={"confirm_all": True})

        # Background wrapper swallows errors and only logs.
        assert response.status_code == 202
