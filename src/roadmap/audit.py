"""Security event logging -- the "events of interest" required by SEC-MON-REQ-1.

This service reads Red Hat Internal and Red Hat Restricted (+PII) data out of
Host Inventory, so Infosec requires that security-relevant events are logged in
a form the Audit and Infosec teams can use for audit and incident response.

Events are emitted on the ``roadmap.security`` logger. In deployed environments
``ROADMAP_JSON_LOGGING`` is "true", so each event is a single JSON object on
stdout and the cluster log forwarder ships it to Splunk. Nothing here writes to
a file or talks to Splunk directly.

Every event carries the record details Infosec asks for:

====================  ==================================================
Required detail       Field
====================  ==================================================
Date and time         ``timestamp`` (ISO 8601, added by the structlog
                      processor chain)
User identification   ``user``, plus ``user_id`` and ``org_id``
Type of event         ``action``
Success or failure    ``result``
Event description     the log message, plus per-event fields
Upstream session data ``request_id``, ``src_ip``, ``x_forwarded_for``,
                      ``true_client_ip``, ``edge_request_id``
====================  ==================================================

The user and network fields are bound once per request as contextvars by the
logging middleware in ``roadmap.main``, so any event raised while handling a
request is attributable without having to plumb the ``Request`` through to the
call site. Events outside a request (startup, shutdown) simply have none.

Field names follow the key=value convention in the Infosec guidelines
(``user``/``action``/``result``/``src_ip``/``x_forwarded_for``) so the Splunk
field extractions are the ones their examples already describe. See
``docs/SECURITY_LOGGING.md`` for the log dictionary handed to the Splunk admins.

The identity header also carries the user's email address and real name. Those
are Red Hat Restricted (+PII) and are deliberately not logged; ``user`` and
``user_id`` are enough to attribute an event.
"""

import base64
import json
import typing as t

import structlog


AUDIT_LOGGER_NAME = "roadmap.security"

audit_logger = structlog.stdlib.get_logger(AUDIT_LOGGER_NAME)

RESULT_SUCCESS = "success"
RESULT_FAILURE = "failure"

# Action names. These are the stable identifiers Splunk searches and alerts are
# built on, so treat them as an interface: add new ones rather than renaming.
#
# Each maps to an event of interest from the Infosec guidelines:
ACTION_DATA_ACCESS = "data.access"  # Accessing RH Internal / Restricted (+PII) data
ACTION_ADMIN = "admin.action"  # Administrative action by a privileged user
ACTION_AUTHZ = "authorization"  # Authorization failures
ACTION_AUTHN = "authentication"  # Invalid login / identity attempts
ACTION_STARTUP = "application.startup"  # Application startup
ACTION_SHUTDOWN = "application.shutdown"  # Application shutdown

# SEC-NET-REQ-5 requires outgoing connections to be logged and held to an
# allow list. See ``roadmap.egress``.
ACTION_EGRESS = "network.egress"  # Outbound connection to an external service
ACTION_EGRESS_DENIED = "network.egress.denied"  # Outbound connection refused by the allow list


def log_audit_event(
    action: str,
    result: str,
    *,
    level: str = "info",
    **fields: t.Any,
) -> None:
    """Emit one event of interest.

    ``action`` is used as both the log message and the ``action`` field, so a
    Splunk search can match the field rather than parse free text. Pass
    ``level="warning"`` for failures and ``level="error"`` for the errors the
    guidelines ask us to raise alongside an event of interest.
    """
    getattr(audit_logger, level)(action, action=action, result=result, **fields)


def _decode_identity(x_rh_identity: str | None) -> dict[str, t.Any]:
    """Decode the identity header, returning {} for anything unusable.

    This duplicates ``roadmap.common._decode_identity`` rather than importing
    it, for two reasons: ``common`` imports this module, and audit logging must
    never raise. A malformed header is itself an event of interest, so we want
    to record it with empty user fields rather than blow up while logging.
    """
    if not x_rh_identity:
        return {}

    try:
        decoded = json.loads(base64.b64decode(x_rh_identity))
    except Exception:
        return {}

    if not isinstance(decoded, dict):
        return {}

    identity = decoded.get("identity")
    return identity if isinstance(identity, dict) else {}


def _mapping(value: t.Any) -> dict[str, t.Any]:
    """Return ``value`` if it is a mapping, otherwise an empty one."""
    return value if isinstance(value, dict) else {}


def principal(x_rh_identity: str | None) -> dict[str, t.Any]:
    """Return the user identification fields for this identity header.

    The keys are always present, even when the header is missing or malformed,
    so Splunk sees a consistent schema and "no identity at all" is searchable
    rather than silent.
    """
    identity = _decode_identity(x_rh_identity)
    # isinstance rather than `or {}`: a truthy non-mapping value, say
    # {"identity": {"user": "bob"}}, would survive `or {}` and then raise on
    # .get() below. _decode_identity guards the two levels above this one for
    # the same reason -- audit logging must never raise, and this runs in the
    # request middleware where it would turn a malformed header into a 500.
    user = _mapping(identity.get("user"))
    service_account = _mapping(identity.get("service_account"))

    return {
        "user": user.get("username") or service_account.get("username"),
        "user_id": user.get("user_id") or service_account.get("client_id"),
        "org_id": identity.get("org_id"),
        "account_number": identity.get("account_number"),
        "identity_type": identity.get("type"),
        "auth_type": identity.get("auth_type"),
        "is_internal": user.get("is_internal"),
        "is_org_admin": user.get("is_org_admin"),
    }


def client_network(headers: t.Mapping[str, str], peer_ip: str | None = None) -> dict[str, t.Any]:
    """Return the caller's network identification.

    ``peer_ip`` (``request.client.host``) is the OpenShift router, not the user,
    because every request reaches the pod through the edge and 3scale. The
    user's address has to come from the forwarding headers, so those are what
    ``src_ip`` is taken from; the peer address is kept separately as
    ``peer_ip`` for infrastructure correlation.

    ``edge_request_id`` is the Akamai/edge identifier, which is what lets an
    event here be joined to the edge logs for the same request.
    """
    forwarded_for = headers.get("x-forwarded-for")
    true_client_ip = headers.get("true-client-ip")

    # X-Forwarded-For is a comma separated list appended to by each hop, so the
    # left-most entry is the original client. Prefer Akamai's True-Client-IP
    # when present, since it is set by the edge rather than by the caller.
    first_forwarded = forwarded_for.split(",")[0].strip() if forwarded_for else None

    return {
        "src_ip": true_client_ip or first_forwarded or peer_ip,
        "x_forwarded_for": forwarded_for,
        "true_client_ip": true_client_ip,
        "peer_ip": peer_ip,
        "edge_request_id": headers.get("x-rh-edge-request-id"),
        "user_agent": headers.get("user-agent"),
    }
