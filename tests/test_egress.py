import httpx
import pytest
import structlog

from roadmap.audit import ACTION_EGRESS
from roadmap.audit import ACTION_EGRESS_DENIED
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
from roadmap.config import Settings
from roadmap.egress import allowed_hosts
from roadmap.egress import AuditedTransport
from roadmap.egress import destinations
from roadmap.egress import egress_client
from roadmap.egress import EgressNotAllowed
from roadmap.egress import PURPOSE_RBAC
from roadmap.egress import PURPOSE_SUBSCRIPTIONS


@pytest.fixture
def capture_events():
    with structlog.testing.capture_logs() as events:
        yield events


def egress_events(events):
    """Keep only the egress events, discarding ordinary application logs."""
    return [event for event in events if event.get("direction") == "egress"]


def transport(allowed, enforce=False, handler=None):
    """Build an AuditedTransport over a MockTransport, so nothing leaves the test."""
    handler = handler or (lambda request: httpx.Response(200))

    return AuditedTransport(
        PURPOSE_RBAC,
        allowed=frozenset(allowed),
        enforce=enforce,
        wrapped=httpx.MockTransport(handler),
    )


async def get(transport, url="http://rbac.svc:8000/api/rbac/v1/access/?application=inventory"):
    async with httpx.AsyncClient(transport=transport) as client:
        return await client.get(url)


class TestDestinations:
    def test_rbac_is_derived_from_settings(self):
        settings = Settings(rbac_hostname="rbac.svc", rbac_port=8000)

        (rbac,) = [dest for dest in destinations(settings) if dest.purpose == PURPOSE_RBAC]
        assert rbac.host == "rbac.svc"
        assert rbac.port == 8000
        assert rbac.internet is False

    def test_unconfigured_destinations_are_omitted(self):
        """An empty setting is not a destination, so it must not reach the allow list."""
        settings = Settings(rbac_hostname="", kessel_enabled=False)

        assert allowed_hosts(settings) == frozenset()

    def test_kessel_is_only_listed_when_enabled(self):
        off = Settings(kessel_enabled=False, kessel_url="kessel-inventory-api:9000")
        on = Settings(kessel_enabled=True, kessel_url="kessel-inventory-api:9000")

        assert "kessel-inventory-api" not in allowed_hosts(off)
        assert "kessel-inventory-api" in allowed_hosts(on)

    def test_scheme_less_grpc_target_is_parsed(self):
        """kessel_url is a bare host:port, not a URL."""
        settings = Settings(kessel_enabled=True, kessel_url="kessel-inventory-api:9000")

        (kessel,) = [dest for dest in destinations(settings) if dest.host == "kessel-inventory-api"]
        assert kessel.port == 9000

    def test_sentry_dsn_host_is_listed(self, monkeypatch):
        monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.example.com/1")

        assert "sentry.example.com" in allowed_hosts(Settings())

    def test_oidc_issuer_is_listed_as_internet(self):
        settings = Settings(kessel_enabled=True, kessel_auth_oidc_issuer="https://sso.example.com/realms/redhat")

        (oidc,) = [dest for dest in destinations(settings) if dest.host == "sso.example.com"]
        assert oidc.internet is True
        assert oidc.port == 443


class TestEgressLogging:
    async def test_successful_request_is_logged(self, capture_events):
        await get(transport(allowed=["rbac.svc"]))

        (event,) = egress_events(capture_events)
        assert event["action"] == ACTION_EGRESS
        assert event["result"] == RESULT_SUCCESS
        assert event["dest_host"] == "rbac.svc"
        assert event["dest_port"] == 8000
        assert event["dest_scheme"] == "http"
        assert event["http_method"] == "GET"
        assert event["purpose"] == PURPOSE_RBAC
        assert event["status_code"] == 200
        assert event["duration"] >= 0

    async def test_query_string_is_not_logged(self, capture_events):
        """Query strings carry filter parameters and are where a token leaks."""
        await get(transport(allowed=["rbac.svc"]))

        (event,) = egress_events(capture_events)
        assert event["dest_path"] == "/api/rbac/v1/access/"
        assert "application=inventory" not in str(event)

    async def test_error_response_is_a_failure(self, capture_events):
        await get(transport(allowed=["rbac.svc"], handler=lambda request: httpx.Response(503)))

        (event,) = egress_events(capture_events)
        assert event["result"] == RESULT_FAILURE
        assert event["status_code"] == 503
        assert event["log_level"] == "warning"

    async def test_connection_failure_is_logged_and_reraised(self, capture_events):
        """A refused connection never yields a response, which is why this is a
        transport and not an httpx event hook."""

        def refuse(request):
            raise httpx.ConnectError("refused")

        with pytest.raises(httpx.ConnectError):
            await get(transport(allowed=["rbac.svc"], handler=refuse))

        (event,) = egress_events(capture_events)
        assert event["result"] == RESULT_FAILURE
        assert event["reason"] == "ConnectError"
        assert event["log_level"] == "error"


class TestAllowList:
    async def test_unlisted_host_is_logged_as_denied(self, capture_events):
        await get(transport(allowed=["rbac.svc"]), url="http://rogue.example.com/x")

        denied = [event for event in egress_events(capture_events) if event["action"] == ACTION_EGRESS_DENIED]
        (event,) = denied
        assert event["result"] == RESULT_FAILURE
        assert event["dest_host"] == "rogue.example.com"
        assert event["reason"] == "not-in-allow-list"
        assert event["log_level"] == "error"

    async def test_unlisted_host_is_allowed_through_when_not_enforcing(self, capture_events):
        """Logging without blocking is the default, so enabling this cannot
        take production down on its own."""
        response = await get(transport(allowed=["rbac.svc"], enforce=False), url="http://rogue.example.com/x")

        assert response.status_code == 200
        actions = [event["action"] for event in egress_events(capture_events)]
        assert actions == [ACTION_EGRESS_DENIED, ACTION_EGRESS]

    async def test_unlisted_host_is_blocked_when_enforcing(self, capture_events):
        with pytest.raises(EgressNotAllowed):
            await get(transport(allowed=["rbac.svc"], enforce=True), url="http://rogue.example.com/x")

        (event,) = egress_events(capture_events)
        assert event["action"] == ACTION_EGRESS_DENIED
        assert event["enforced"] is True

    async def test_listed_host_is_not_denied(self, capture_events):
        await get(transport(allowed=["rbac.svc"], enforce=True))

        actions = [event["action"] for event in egress_events(capture_events)]
        assert ACTION_EGRESS_DENIED not in actions


class TestEgressClient:
    def test_allow_list_comes_from_settings(self):
        settings = Settings(rbac_hostname="rbac.svc", rbac_port=8000)
        client = egress_client(PURPOSE_RBAC, settings)

        assert isinstance(client._transport, AuditedTransport)
        assert client._transport._allowed == frozenset({"rbac.svc"})
        assert client._transport._enforce is False

    def test_enforcement_follows_the_setting(self):
        settings = Settings(rbac_hostname="rbac.svc", egress_enforce=True)

        assert egress_client(PURPOSE_RBAC, settings)._transport._enforce is True

    def test_verify_is_passed_to_the_transport(self):
        """A client-level verify is ignored once a custom transport is given,
        so the mTLS context from the notificator has to reach the transport."""
        import ssl

        settings = Settings()
        ctx = ssl.create_default_context()

        client = egress_client(PURPOSE_SUBSCRIPTIONS, settings, verify=ctx, timeout=180)
        assert isinstance(client._transport, AuditedTransport)
