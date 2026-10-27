import base64
import io
import json
import logging

import pytest
import structlog

from roadmap.audit import ACTION_ADMIN
from roadmap.audit import ACTION_AUTHN
from roadmap.audit import ACTION_AUTHZ
from roadmap.audit import ACTION_DATA_ACCESS
from roadmap.audit import audit_logger
from roadmap.audit import AUDIT_LOGGER_NAME
from roadmap.audit import client_network
from roadmap.audit import log_audit_event
from roadmap.audit import principal
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
from roadmap.common import get_allowed_host_groups
from roadmap.config import Settings


LIFECYCLE_CUSTOM_URL = "/api/roadmap/admin/notifications/lifecycle/custom"


def encode_identity(identity):
    return base64.b64encode(json.dumps({"identity": identity}).encode()).decode()


def audit_events(events):
    """Keep only the events of interest, discarding ordinary application logs."""
    return [event for event in events if "action" in event]


@pytest.fixture
def capture_events():
    """Capture the events emitted by log_audit_event."""
    with structlog.testing.capture_logs() as events:
        yield events


@pytest.fixture(autouse=True)
def clear_contextvars():
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def configured_logging_at():
    """Run setup_logging for real, then put global logging state back.

    Returns a callable that configures logging and hands back the buffer the
    rendered records land in. The handler setup_logging installs is pointed at
    that buffer rather than stderr, so the records can be read back without
    depending on how pytest is capturing output.

    The teardown matters: setup_logging adds a root handler and reconfigures
    structlog globally, so leaving it in place would make every later test emit
    duplicate records.
    """
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    original_audit_level = logging.getLogger(AUDIT_LOGGER_NAME).level

    def _reset_logger_cache():
        """Make the audit logger pick up a newly configured processor chain.

        setup_logging passes cache_logger_on_first_use=True, and structlog
        implements that by replacing the lazy proxy's own bind method the first
        time it is used. Reconfiguring does not undo that, so the proxy would
        keep rendering through whichever chain a previous test assembled.
        """
        audit_logger.__dict__.pop("bind", None)

    def _configure(log_level="info"):
        from roadmap.custom_logging import setup_logging

        root.handlers.clear()
        _reset_logger_cache()
        setup_logging(json_logs=True, log_level=log_level)

        buffer = io.StringIO()
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setStream(buffer)

        return buffer

    yield _configure

    root.handlers[:] = original_handlers
    root.setLevel(original_level)
    logging.getLogger(AUDIT_LOGGER_NAME).setLevel(original_audit_level)
    structlog.reset_defaults()
    _reset_logger_cache()


@pytest.fixture
def configured_logging(configured_logging_at):
    return configured_logging_at("info")


class TestPrincipal:
    def test_user_identity(self):
        identity = encode_identity(
            {
                "org_id": "12345",
                "account_number": "67890",
                "type": "User",
                "auth_type": "jwt-auth",
                "user": {"username": "rmonk", "user_id": "u-1", "is_internal": True, "is_org_admin": False},
            }
        )

        assert principal(identity) == {
            "user": "rmonk",
            "user_id": "u-1",
            "org_id": "12345",
            "account_number": "67890",
            "identity_type": "User",
            "auth_type": "jwt-auth",
            "is_internal": True,
            "is_org_admin": False,
        }

    def test_service_account_identity(self):
        """A service account has no username under "user", so fall back to it."""
        identity = encode_identity(
            {
                "org_id": "12345",
                "type": "ServiceAccount",
                "service_account": {"username": "service-account-x", "client_id": "client-1"},
            }
        )
        fields = principal(identity)

        assert fields["user"] == "service-account-x"
        assert fields["user_id"] == "client-1"

    def test_pii_is_not_logged(self):
        """Email and real name are Red Hat Restricted (+PII) and must not appear."""
        identity = encode_identity(
            {
                "org_id": "12345",
                "user": {
                    "username": "rmonk",
                    "email": "rmonk@redhat.com",
                    "first_name": "Rich",
                    "last_name": "Monk",
                },
            }
        )

        assert "rmonk@redhat.com" not in json.dumps(principal(identity))
        assert "Rich" not in json.dumps(principal(identity))

    @pytest.mark.parametrize(
        "header",
        (
            pytest.param(None, id="missing"),
            pytest.param("", id="empty"),
            pytest.param("not-base64!", id="not-base64"),
            pytest.param(base64.b64encode(b"not json").decode(), id="not-json"),
            pytest.param(base64.b64encode(b'["a", "list"]').decode(), id="not-an-object"),
            pytest.param(base64.b64encode(b'{"identity": "a string"}').decode(), id="identity-not-an-object"),
        ),
    )
    def test_unusable_header_gives_empty_fields(self, header):
        """A bad header is itself an event of interest, so this must not raise."""
        fields = principal(header)

        assert set(fields) == {
            "user",
            "user_id",
            "org_id",
            "account_number",
            "identity_type",
            "auth_type",
            "is_internal",
            "is_org_admin",
        }
        assert all(value is None for value in fields.values())

    @pytest.mark.parametrize(
        "identity",
        (
            pytest.param({"user": "a string", "org_id": "123"}, id="user-not-an-object"),
            pytest.param({"user": ["a", "list"], "org_id": "123"}, id="user-is-a-list"),
            pytest.param({"service_account": "a string", "org_id": "123"}, id="service-account-not-an-object"),
            pytest.param({"user": 0.0, "org_id": "123"}, id="user-is-a-number"),
        ),
    )
    def test_nested_values_that_are_not_objects(self, identity):
        """`or {}` would let a truthy non-mapping through and raise on .get().

        The guard has to hold at every level, not just the top: this runs in
        the request middleware, so raising here turns a malformed header into
        a 500 rather than an event of interest.
        """
        fields = principal(encode_identity(identity))

        assert fields["user"] is None
        assert fields["user_id"] is None
        assert fields["is_internal"] is None
        # Sibling fields stay readable -- only the unusable branch is dropped.
        assert fields["org_id"] == "123"


class TestClientNetwork:
    def test_true_client_ip_wins(self):
        """True-Client-IP is set by the edge, so it is trusted over the caller's own header."""
        headers = {"true-client-ip": "1.2.3.4", "x-forwarded-for": "9.9.9.9, 55.66.3.2"}

        assert client_network(headers, peer_ip="10.128.0.9")["src_ip"] == "1.2.3.4"

    def test_falls_back_to_first_forwarded_for(self):
        headers = {"x-forwarded-for": "1.2.3.4, 55.66.3.2"}

        assert client_network(headers, peer_ip="10.128.0.9")["src_ip"] == "1.2.3.4"

    def test_falls_back_to_peer_ip(self):
        assert client_network({}, peer_ip="10.128.0.9")["src_ip"] == "10.128.0.9"

    def test_peer_ip_is_kept_separately(self):
        """The router address stays available even when the user's address is known."""
        fields = client_network({"true-client-ip": "1.2.3.4"}, peer_ip="10.128.0.9")

        assert fields["src_ip"] == "1.2.3.4"
        assert fields["peer_ip"] == "10.128.0.9"

    def test_no_network_information(self):
        fields = client_network({})

        assert all(value is None for value in fields.values())

    def test_edge_request_id(self):
        assert client_network({"x-rh-edge-request-id": "edge-1"})["edge_request_id"] == "edge-1"


class TestLogAuditEvent:
    def test_action_and_result(self, capture_events):
        log_audit_event(ACTION_DATA_ACCESS, RESULT_SUCCESS, resource="host_inventory")

        (event,) = capture_events
        assert event["action"] == ACTION_DATA_ACCESS
        assert event["result"] == RESULT_SUCCESS
        assert event["resource"] == "host_inventory"
        assert event["log_level"] == "info"

    def test_failure_level(self, capture_events):
        log_audit_event(ACTION_DATA_ACCESS, RESULT_FAILURE, level="error", error_code=500)

        (event,) = capture_events
        assert event["result"] == RESULT_FAILURE
        assert event["log_level"] == "error"

    def test_bound_context_is_included(self, configured_logging):
        """User and IP are bound per request, so call sites do not pass them.

        This goes through the real processor chain rather than
        ``capture_logs``, because it is ``merge_contextvars`` in that chain
        that pulls the bound values in.
        """
        structlog.contextvars.bind_contextvars(user="rmonk", src_ip="1.2.3.4")
        log_audit_event(ACTION_DATA_ACCESS, RESULT_SUCCESS)

        record = json.loads(configured_logging.getvalue().strip())
        assert record["user"] == "rmonk"
        assert record["src_ip"] == "1.2.3.4"
        assert record["action"] == ACTION_DATA_ACCESS
        assert record["logger"] == AUDIT_LOGGER_NAME

    def test_required_record_details_are_present(self, configured_logging):
        """The details Infosec requires on every event of interest."""
        structlog.contextvars.bind_contextvars(
            request_id="req-1", **principal(encode_identity({"org_id": "12345", "user": {"username": "rmonk"}}))
        )
        log_audit_event(ACTION_DATA_ACCESS, RESULT_SUCCESS)

        record = json.loads(configured_logging.getvalue().strip())
        # Date and time, user identification, type of event, success/failure,
        # description, and upstream session data.
        for field in ("timestamp", "user", "org_id", "action", "result", "message", "request_id"):
            assert field in record, field


def test_audit_logger_survives_a_raised_log_level(configured_logging_at):
    """Audit events are a compliance requirement, not a debugging aid."""
    configured_logging_at("critical")

    assert logging.getLogger(AUDIT_LOGGER_NAME).isEnabledFor(logging.INFO)


class TestAdminAuditEvents:
    """The /admin routes are the privileged surface, so every outcome is recorded."""

    @pytest.fixture(autouse=True)
    def _force_prod(self, monkeypatch):
        """The internal-user check only runs in prod."""
        monkeypatch.setenv("ROADMAP_ENV_NAME", "prod")
        Settings.create.cache_clear()
        yield
        Settings.create.cache_clear()

    def test_missing_identity_is_an_authentication_failure(self, client, capture_events):
        response = client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1})

        assert response.status_code == 401
        (event,) = audit_events(capture_events)
        assert event["action"] == ACTION_AUTHN
        assert event["result"] == RESULT_FAILURE
        assert event["error_code"] == 401
        assert event["reason"] == "missing-identity"
        assert event["endpoint"] == f"POST {LIFECYCLE_CUSTOM_URL}"

    def test_invalid_identity_is_an_authentication_failure(self, client, capture_events):
        response = client.post(
            LIFECYCLE_CUSTOM_URL, json={"org_ids": 1}, headers={"x-rh-identity": "not-valid-base64!!!"}
        )

        assert response.status_code == 401
        (event,) = audit_events(capture_events)
        assert event["action"] == ACTION_AUTHN
        assert event["reason"] == "invalid-identity"

    def test_external_user_is_an_authorization_failure(self, client, capture_events):
        headers = {"x-rh-identity": encode_identity({"org_id": "1", "user": {"username": "ext", "is_internal": False}})}
        response = client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1}, headers=headers)

        assert response.status_code == 403
        (event,) = audit_events(capture_events)
        assert event["action"] == ACTION_AUTHZ
        assert event["result"] == RESULT_FAILURE
        assert event["error_code"] == 403
        assert event["reason"] == "not-internal"

    def test_internal_user_records_the_administrative_action(self, client, capture_events, mocker):
        mocker.patch("roadmap.admin.notifications.lifecycle.kind.send", new_callable=mocker.AsyncMock)
        headers = {
            "x-rh-identity": encode_identity({"org_id": "1", "user": {"username": "rmonk", "is_internal": True}})
        }
        client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1}, headers=headers)

        event = audit_events(capture_events)[0]
        assert event["action"] == ACTION_ADMIN
        assert event["result"] == RESULT_SUCCESS
        assert event["authorization"] == "internal-user"
        assert event["endpoint"] == f"POST {LIFECYCLE_CUSTOM_URL}"

    def test_non_prod_records_that_the_check_was_skipped(self, client, capture_events, monkeypatch, mocker):
        """A skipped check must not look like a verified admin action."""
        mocker.patch("roadmap.admin.notifications.lifecycle.kind.send", new_callable=mocker.AsyncMock)
        monkeypatch.setenv("ROADMAP_ENV_NAME", "stage")
        Settings.create.cache_clear()

        client.post(LIFECYCLE_CUSTOM_URL, json={"org_ids": 1})

        event = audit_events(capture_events)[0]
        assert event["action"] == ACTION_ADMIN
        assert event["authorization"] == "skipped-non-prod"


class TestAuthorizationFailureEvents:
    async def test_denial_is_recorded(self, capture_events):
        """A caller with no inventory permission is denied, and that is recorded."""
        settings = Settings(dev=False, kessel_enabled=False, rbac_hostname="")

        with pytest.raises(Exception) as excinfo:
            await get_allowed_host_groups(settings, x_rh_identity=None)

        assert excinfo.value.status_code == 403
        (event,) = audit_events(capture_events)
        assert event["action"] == ACTION_AUTHZ
        assert event["result"] == RESULT_FAILURE
        assert event["error_code"] == 403
        assert event["resource"] == "host_inventory"
        assert event["authz_backend"] == "rbac_v1"
        assert event["log_level"] == "warning"

    async def test_authorization_service_error_is_recorded_at_error_level(self, capture_events, mocker):
        """A failing RBAC call is how a denial would go unrecorded, so it is an error."""
        from fastapi import HTTPException

        mocker.patch("roadmap.common.query_rbac", side_effect=HTTPException(status_code=502, detail="boom"))
        settings = Settings(dev=False, kessel_enabled=False)

        with pytest.raises(HTTPException):
            await get_allowed_host_groups(settings, x_rh_identity=None)

        (event,) = audit_events(capture_events)
        assert event["action"] == ACTION_AUTHZ
        assert event["error_code"] == 502
        assert event["log_level"] == "error"
