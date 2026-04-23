"""Tests for notificator.subscriptions — org ID resolution and API fetching."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import httpx
import pytest

from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION
from notificator.notificator_config import SubscriptionType
from notificator.subscriptions import fetch_subscribed_org_ids
from notificator.subscriptions import get_org_ids


def _make_settings(*, dev=False, subscriptions_url="https://example.com/subscriptions"):
    return SimpleNamespace(
        subscriptions_url=subscriptions_url,
        tls_cert_path="/tmp/tls/cert.pem",
        tls_key_path="/tmp/tls/key.pem",
        dev=dev,
    )


def _mock_client(mocker, *, status_code=200, json_data=None):
    """Patch httpx.AsyncClient to return a canned response without network I/O."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}

    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"{status_code}",
            request=httpx.Request("GET", "https://test"),
            response=httpx.Response(status_code),
        )
    else:
        response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.get.return_value = response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    mock_cls = mocker.patch("notificator.subscriptions.httpx.AsyncClient", return_value=mock_client)
    return mock_client, mock_cls


class TestGetOrgIds:
    """get_org_ids: precedence of explicit override, dev mode, and API fetch."""

    def _patch_settings(self, mocker, *, dev=False):
        settings = _make_settings(dev=dev)
        mocker.patch("notificator.subscriptions.NotificatorSettings.create", return_value=settings)
        return settings

    async def test_explicit_org_ids_returned_directly(self):
        result = await get_org_ids(LIFECYCLE_SUBSCRIPTION, org_ids=[42, 99])

        assert result == [42, 99]

    async def test_dev_mode_returns_dev_org_ids(self, mocker):
        self._patch_settings(mocker, dev=True)

        result = await get_org_ids(LIFECYCLE_SUBSCRIPTION)

        assert result == [1234]

    async def test_dev_mode_returns_copy(self, mocker):
        """DEV_ORG_IDS is not returned by reference — mutations won't leak."""
        self._patch_settings(mocker, dev=True)

        first = await get_org_ids(LIFECYCLE_SUBSCRIPTION)
        first.append(9999)
        second = await get_org_ids(LIFECYCLE_SUBSCRIPTION)

        assert second == [1234]

    async def test_explicit_org_ids_skip_settings_lookup(self, mocker):
        """Explicit org_ids returns before NotificatorSettings.create() is called."""
        create_mock = mocker.patch("notificator.subscriptions.NotificatorSettings.create")

        result = await get_org_ids(LIFECYCLE_SUBSCRIPTION, org_ids=[999])

        assert result == [999]
        create_mock.assert_not_called()

    async def test_fetches_from_api_when_not_dev(self, mocker):
        self._patch_settings(mocker, dev=False)
        fetch_mock = mocker.patch(
            "notificator.subscriptions.fetch_subscribed_org_ids",
            return_value=[111, 222],
        )

        result = await get_org_ids(LIFECYCLE_SUBSCRIPTION)

        assert result == [111, 222]
        fetch_mock.assert_called_once()

    async def test_forwards_subscription_to_fetch(self, mocker):
        settings = self._patch_settings(mocker, dev=False)
        fetch_mock = mocker.patch(
            "notificator.subscriptions.fetch_subscribed_org_ids",
            return_value=[],
        )
        other = SubscriptionType("other-app", "some-other-event-type")

        await get_org_ids(other)

        fetch_mock.assert_called_once_with(settings, other)


class TestFetchSubscribedOrgIds:
    """fetch_subscribed_org_ids: mTLS HTTP call and response parsing."""

    @pytest.fixture
    def settings(self):
        return _make_settings()

    async def test_returns_org_ids_as_ints(self, mocker, settings):
        _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: ["111", "222", "333"]})

        result = await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        assert result == [111, 222, 333]

    async def test_returns_empty_list_when_key_missing(self, mocker, settings):
        _mock_client(mocker, json_data={"other-event": ["999"]})

        result = await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        assert result == []

    async def test_returns_empty_list_for_empty_array(self, mocker, settings):
        _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: []})

        result = await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        assert result == []

    async def test_raises_on_http_error(self, mocker, settings):
        _mock_client(mocker, status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

    async def test_builds_url_from_base_and_application(self, mocker, settings):
        client, _ = _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: ["42"]})

        await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        client.get.assert_called_once_with(
            f"{settings.subscriptions_url}/{LIFECYCLE_SUBSCRIPTION.application}",
            params={"eventTypeNames": LIFECYCLE_SUBSCRIPTION.event_type},
        )

    async def test_uses_mtls_cert_from_settings(self, mocker, settings):
        _, mock_cls = _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: []})

        await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        mock_cls.assert_called_once_with(cert=("/tmp/tls/cert.pem", "/tmp/tls/key.pem"))

    async def test_different_subscription_uses_correct_key_and_path(self, mocker, settings):
        other = SubscriptionType("other-app", "some-other-event")
        _mock_client(mocker, json_data={other.event_type: ["555", "666"]})

        result = await fetch_subscribed_org_ids(settings, other)

        assert result == [555, 666]

    async def test_raises_with_clear_error_when_payload_contains_non_int(self, mocker, settings):
        _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: ["111", "oops", "333"]})

        with pytest.raises(ValueError, match="Invalid subscriptions payload"):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

    async def test_raises_when_subscriptions_url_not_configured(self):
        settings = _make_settings(subscriptions_url=None)

        with pytest.raises(RuntimeError, match="ROADMAP_SUBSCRIPTIONS_URL is not configured"):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)
