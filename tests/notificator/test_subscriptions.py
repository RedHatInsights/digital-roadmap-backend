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
        tls_cert_path="/some/path/cert.pem",
        tls_key_path="/some/path/key.pem",
        dev=dev,
    )


def _mock_client(mocker, *, status_code=200, json_data=None):
    """Patch httpx.AsyncClient and ssl to return canned responses without I/O."""
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

    ssl_ctx = MagicMock()
    ssl_create = mocker.patch(
        "notificator.subscriptions.ssl.create_default_context",
        return_value=ssl_ctx,
    )

    return mock_client, mock_cls, ssl_ctx, ssl_create


class TestGetOrgIds:
    """get_org_ids: dev mode vs API fetch."""

    def _patch_settings(self, mocker, *, dev=False):
        settings = _make_settings(dev=dev)
        mocker.patch("notificator.subscriptions.NotificatorSettings.create", return_value=settings)
        return settings

    async def test_dev_mode_returns_dev_org_ids(self, mocker):
        self._patch_settings(mocker, dev=True)

        result = await get_org_ids(LIFECYCLE_SUBSCRIPTION)

        assert result == [1234]

    async def test_dev_mode_returns_copy(self, mocker):
        """DEV_ORG_IDS is not returned by reference - mutations won't leak."""
        self._patch_settings(mocker, dev=True)

        first = await get_org_ids(LIFECYCLE_SUBSCRIPTION)
        first.append(9999)
        second = await get_org_ids(LIFECYCLE_SUBSCRIPTION)

        assert second == [1234]

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

    @pytest.mark.parametrize(
        "json_data",
        [
            pytest.param({"other-event": ["999"]}, id="key_missing"),
            pytest.param({LIFECYCLE_SUBSCRIPTION.event_type: []}, id="empty_array"),
        ],
    )
    async def test_returns_empty_list(self, mocker, settings, json_data):
        _mock_client(mocker, json_data=json_data)

        result = await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        assert result == []

    async def test_raises_on_http_error(self, mocker, settings):
        _mock_client(mocker, status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

    async def test_builds_url_from_base_and_application(self, mocker, settings):
        client, *_ = _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: ["42"]})

        await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        client.get.assert_called_once_with(
            f"{settings.subscriptions_url}/subscriptions/rhel/{LIFECYCLE_SUBSCRIPTION.application}",
            params={"eventTypeNames": LIFECYCLE_SUBSCRIPTION.event_type},
        )

    async def test_uses_mtls_cert_from_settings(self, mocker, settings):
        _, mock_cls, ssl_ctx, ssl_create = _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: []})

        await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

        ssl_create.assert_called_once()
        ssl_ctx.load_cert_chain.assert_called_once_with(certfile=settings.tls_cert_path, keyfile=settings.tls_key_path)
        mock_cls.assert_called_once_with(verify=ssl_ctx, timeout=180, proxy="http://squid.corp.redhat.com:3128")

    async def test_different_subscription_uses_correct_key_and_path(self, mocker, settings):
        other = SubscriptionType("other-app", "some-other-event")
        _mock_client(mocker, json_data={other.event_type: ["555", "666"]})

        result = await fetch_subscribed_org_ids(settings, other)

        assert result == [555, 666]

    @pytest.mark.parametrize(
        "bad_value",
        [
            pytest.param("oops", id="non_int_string"),
            pytest.param(None, id="none"),
        ],
    )
    async def test_raises_on_invalid_payload_element(self, mocker, settings, bad_value):
        _mock_client(mocker, json_data={LIFECYCLE_SUBSCRIPTION.event_type: ["111", bad_value, "333"]})

        with pytest.raises(ValueError, match="Invalid subscriptions payload"):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)

    async def test_raises_when_subscriptions_url_not_configured(self):
        settings = _make_settings(subscriptions_url=None)

        with pytest.raises(RuntimeError, match="ROADMAP_SUBSCRIPTIONS_URL is not configured"):
            await fetch_subscribed_org_ids(settings, LIFECYCLE_SUBSCRIPTION)
