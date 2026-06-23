"""Tests for admin notification endpoints (lifecycle and roadmap)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from notificator.kafka import KafkaBrokersNotConfigured
from roadmap.admin.notifications.lifecycle import kind as lifecycle_kind
from roadmap.admin.notifications.roadmap import kind as roadmap_kind
from roadmap.config import Settings


LIFECYCLE_CUSTOM_URL = "/api/roadmap/admin/notifications/lifecycle/custom"
LIFECYCLE_ALL_URL = "/api/roadmap/admin/notifications/lifecycle/all"
LIFECYCLE_SUBSCRIBED_URL = "/api/roadmap/admin/notifications/lifecycle/subscribed-orgs"

ROADMAP_CUSTOM_URL = "/api/roadmap/admin/notifications/roadmap/custom"
ROADMAP_ALL_URL = "/api/roadmap/admin/notifications/roadmap/all"
ROADMAP_SUBSCRIBED_URL = "/api/roadmap/admin/notifications/roadmap/subscribed-orgs"


@pytest.fixture(autouse=True)
def mock_lifecycle_send(mocker):
    """Prevent real lifecycle notification calls in all tests."""
    return mocker.patch.object(lifecycle_kind, "send", new_callable=AsyncMock)


@pytest.fixture(autouse=True)
def mock_roadmap_send(mocker):
    """Prevent real roadmap notification calls in all tests."""
    return mocker.patch.object(roadmap_kind, "send", new_callable=AsyncMock)


@pytest.fixture()
def mock_get_org_ids(mocker):
    return mocker.patch("roadmap.admin.notifications.get_org_ids", new_callable=AsyncMock)


@pytest.fixture()
def _force_prod(monkeypatch):
    """Set env_name to 'prod' so the auth guard is active."""
    monkeypatch.setenv("ROADMAP_ENV_NAME", "prod")
    Settings.create.cache_clear()
    yield
    Settings.create.cache_clear()


@dataclass
class NotificationEndpoints:
    label: str
    custom_url: str
    all_url: str
    subscribed_url: str
    mock_send: AsyncMock


@pytest.fixture(params=["lifecycle", "roadmap"])
def endpoints(request, mock_lifecycle_send, mock_roadmap_send):
    """Parametrized fixture providing URLs and mock for each notification type."""
    if request.param == "lifecycle":
        return NotificationEndpoints(
            label="lifecycle",
            custom_url=LIFECYCLE_CUSTOM_URL,
            all_url=LIFECYCLE_ALL_URL,
            subscribed_url=LIFECYCLE_SUBSCRIBED_URL,
            mock_send=mock_lifecycle_send,
        )
    elif request.param == "roadmap":
        return NotificationEndpoints(
            label="roadmap",
            custom_url=ROADMAP_CUSTOM_URL,
            all_url=ROADMAP_ALL_URL,
            subscribed_url=ROADMAP_SUBSCRIBED_URL,
            mock_send=mock_roadmap_send,
        )
    else:
        raise ValueError(f"Invalid notification type: {request.param}")


# -- Auth guard (router-level, tested once with lifecycle endpoints) -----------


class TestAdminAuthGuardProd:
    """In prod, the is_internal check must block unauthenticated and external callers."""

    @pytest.fixture(autouse=True)
    def _prod(self, _force_prod):
        pass

    def test_no_identity_header_returns_401(self, client):
        response = client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1})

        assert response.status_code == 401
        assert "Missing x-rh-identity" in response.json()["detail"]

    def test_invalid_identity_header_returns_401(self, client):
        response = client.post(
            LIFECYCLE_CUSTOM_URL,
            json={"org_ids": 1},
            headers={"x-rh-identity": "not-valid-base64!!!"},
        )

        assert response.status_code == 401
        assert "Invalid x-rh-identity" in response.json()["detail"]

    def test_external_user_returns_403(self, client, external_headers):
        response = client.post(
            LIFECYCLE_CUSTOM_URL,
            json={"org_ids": 1},
            headers=external_headers,
        )

        assert response.status_code == 403
        assert "restricted to internal users" in response.json()["detail"]

    def test_external_user_blocked_on_get(self, client, external_headers):
        response = client.get(LIFECYCLE_SUBSCRIBED_URL, headers=external_headers)

        assert response.status_code == 403

    def test_internal_user_passes(self, admin_client):
        response = admin_client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1})

        assert response.status_code == 200


class TestAdminAuthGuardStage:
    """In stage (default), the auth guard is bypassed."""

    def test_no_header_allowed_in_stage(self, client):
        response = client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1})

        assert response.status_code == 200

    def test_external_user_allowed_in_stage(self, client, external_headers):
        response = client.post(
            LIFECYCLE_CUSTOM_URL,
            json={"org_ids": 1},
            headers=external_headers,
        )

        assert response.status_code == 200


# -- Request validation (shared Pydantic models, tested once) ------------------


class TestCustomEndpointValidation:
    def test_missing_body_returns_422(self, admin_client):
        response = admin_client.post(LIFECYCLE_CUSTOM_URL)

        assert response.status_code == 422

    def test_invalid_org_ids_type_returns_422(self, admin_client):
        response = admin_client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": "not-an-int"})

        assert response.status_code == 422

    def test_empty_org_ids_returns_422(self, admin_client):
        response = admin_client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": []})

        assert response.status_code == 422


# -- Trigger endpoints (parametrized over both notification types) -------------


class TestTriggerNotification:
    def test_custom_success_single_org(self, admin_client, endpoints):
        response = admin_client.post(endpoints.custom_url, json={"org_ids": 42})

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "message": f"{endpoints.label.capitalize()} notification completed",
            "requested_org_ids": [42],
        }
        endpoints.mock_send.assert_awaited_once_with(override_org_ids=[42])

    def test_custom_deduplicates_and_sorts_org_ids(self, admin_client, endpoints):
        response = admin_client.post(endpoints.custom_url, json={"org_ids": [3, 1, 3, 2]})

        assert response.status_code == 200
        assert response.json()["requested_org_ids"] == [1, 2, 3]
        endpoints.mock_send.assert_awaited_once_with(override_org_ids=[1, 2, 3])

    def test_custom_runtime_failure(self, admin_client, endpoints):
        endpoints.mock_send.side_effect = RuntimeError("failed for 1/1 orgs")

        response = admin_client.post(endpoints.custom_url, json={"org_ids": 42})

        assert response.status_code == 500
        assert "failed for 1/1 orgs" in response.json()["detail"]

    def test_custom_kafka_not_configured(self, admin_client, endpoints):
        endpoints.mock_send.side_effect = KafkaBrokersNotConfigured("no brokers")

        response = admin_client.post(endpoints.custom_url, json={"org_ids": 42})

        assert response.status_code == 503
        assert "Kafka brokers not configured" in response.json()["detail"]

    def test_all_requires_confirmation(self, admin_client, endpoints):
        response = admin_client.post(endpoints.all_url, json={"confirm_all": False})

        assert response.status_code == 400
        assert "confirm_all=true" in response.json()["detail"]

    def test_all_accepts_and_triggers_background(self, admin_client, endpoints):
        response = admin_client.post(endpoints.all_url, json={"confirm_all": True})

        assert response.status_code == 202
        assert response.json() == {"message": f"{endpoints.label.capitalize()} notification accepted"}
        endpoints.mock_send.assert_awaited_once_with(override_org_ids=None)

    def test_all_background_failure_still_returns_202(self, admin_client, endpoints):
        endpoints.mock_send.side_effect = RuntimeError("batch failed")

        response = admin_client.post(endpoints.all_url, json={"confirm_all": True})

        assert response.status_code == 202
        endpoints.mock_send.assert_awaited_once_with(override_org_ids=None)


# -- Subscribed orgs endpoint (parametrized) -----------------------------------


class TestSubscribedOrgs:
    def test_returns_subscribed_org_ids(self, admin_client, endpoints, mock_get_org_ids):
        mock_get_org_ids.return_value = [1, 2, 3]

        response = admin_client.get(endpoints.subscribed_url)

        assert response.status_code == 200
        assert response.json() == {"org_ids": [1, 2, 3], "count": 3}

    def test_returns_empty_list_when_no_subscriptions(self, admin_client, endpoints, mock_get_org_ids):
        mock_get_org_ids.return_value = []

        response = admin_client.get(endpoints.subscribed_url)

        assert response.status_code == 200
        assert response.json() == {"org_ids": [], "count": 0}

    def test_returns_503_when_subscriptions_url_not_configured(self, admin_client, endpoints, mock_get_org_ids):
        mock_get_org_ids.side_effect = RuntimeError("ROADMAP_SUBSCRIPTIONS_URL is not configured")

        response = admin_client.get(endpoints.subscribed_url)

        assert response.status_code == 503
        assert "ROADMAP_SUBSCRIPTIONS_URL is not configured" in response.json()["detail"]

    def test_returns_500_on_unexpected_error(self, admin_client, endpoints, mock_get_org_ids):
        mock_get_org_ids.side_effect = Exception("connection timeout")

        response = admin_client.get(endpoints.subscribed_url)

        assert response.status_code == 500
        assert "Failed to fetch subscribed org IDs" in response.json()["detail"]
