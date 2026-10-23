"""Outbound connection logging and allow-listing -- SEC-NET-REQ-5.

The control has three parts. Only the first and third are things an application
can do; the second is infrastructure. What this module provides:

1. **Log the connection details.** Every outbound HTTP(S) request made through
   :func:`egress_client` emits a ``network.egress`` event of interest on the
   ``roadmap.security`` logger, which the cluster log forwarder ships to Splunk
   along with the SEC-MON-REQ-1 events. See ``roadmap.audit``.

2. **Consume Infosec deny lists.** Not implementable here. Blocking connections
   to rogue hosts is done by the egress proxy and DNS resolvers the pod uses,
   which are cluster-level and owned by app-sre. See ``docs/EGRESS_MONITORING.md``.

3. **Enforce an allow list.** :func:`allowed_hosts` is the application owner's
   pre-authorised list of destinations. It is *derived from configuration*
   rather than hard-coded, because every destination this service talks to
   comes from a setting or a Clowder-injected endpoint -- no caller-supplied
   URL ever reaches an HTTP client, so there is no request-driven egress to
   enumerate and no SSRF surface. A request to a host outside the list is
   always logged as ``network.egress.denied``; whether it is also *blocked*
   depends on ``ROADMAP_EGRESS_ENFORCE``.

``ROADMAP_EGRESS_ENFORCE`` defaults to false so that turning this on cannot by
itself take production down: the denial is recorded either way, and the list
can be verified against real traffic in Splunk before the block is switched on.

Only the scheme, host, port and path of a request are logged. Query strings are
deliberately excluded -- they carry filter parameters and are the usual place
for a token to leak into a log -- and no request headers are logged, because
the RBAC call forwards the caller's ``X-RH-Identity``.
"""

import os
import time
import typing as t

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from roadmap.audit import ACTION_EGRESS
from roadmap.audit import ACTION_EGRESS_DENIED
from roadmap.audit import log_audit_event
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
from roadmap.config import Settings


# Purposes. Used as the ``purpose`` field on every egress event, so a Splunk
# search can tell which dependency a connection was for without matching on
# hostnames that differ per environment.
PURPOSE_RBAC = "rbac"
PURPOSE_SUBSCRIPTIONS = "notifications-gateway"
PURPOSE_KESSEL = "kessel-inventory"
PURPOSE_KESSEL_OIDC = "kessel-oidc"
PURPOSE_SENTRY = "sentry"


class EgressNotAllowed(Exception):
    """Raised when a connection to a host outside the allow list is blocked."""


@dataclass(frozen=True)
class Destination:
    """One pre-authorised outbound destination.

    ``internet`` distinguishes the connections the control is actually about
    from in-cluster service-to-service traffic, which never leaves the cluster
    and is governed by network policy rather than by egress rules.
    """

    purpose: str
    host: str
    port: int | None
    protocol: str
    internet: bool
    description: str


def _split_host_port(value: str | None) -> tuple[str | None, int | None]:
    """Return (host, port) for a URL or a bare ``host:port``.

    ``kessel_url`` is a gRPC target with no scheme, so urlsplit needs the
    leading ``//`` to treat it as an authority rather than a path.
    """
    if not value or not value.strip():
        return None, None

    value = value.strip()
    if "//" not in value:
        value = f"//{value}"

    try:
        parts = urlsplit(value)
        return parts.hostname, parts.port
    except ValueError:
        # A malformed setting must not break request handling. The host stays
        # unknown, which means it will not match the allow list and will be
        # recorded as a denial -- the correct outcome for a destination we
        # cannot identify.
        return None, None


def destinations(settings: Settings) -> list[Destination]:
    """Return every outbound destination this process is configured to reach.

    Built from live settings, so it reflects what the running pod will actually
    do rather than what a checked-in list claims. Destinations that are not
    configured in this environment are omitted: Kessel is off by default, and
    the notificator settings only exist in the notificator job.
    """
    found: list[Destination] = []

    rbac_host, rbac_port = _split_host_port(settings.rbac_url)
    if rbac_host:
        found.append(
            Destination(
                purpose=PURPOSE_RBAC,
                host=rbac_host,
                port=rbac_port or 80,
                protocol="http",
                internet=False,
                description="RBAC v1 access check. Clowder-injected in-cluster service.",
            )
        )

    # subscriptions_url only exists on NotificatorSettings.
    subs_host, subs_port = _split_host_port(getattr(settings, "subscriptions_url", None))
    if subs_host:
        found.append(
            Destination(
                purpose=PURPOSE_SUBSCRIPTIONS,
                host=subs_host,
                port=subs_port or 443,
                protocol="https (mTLS)",
                internet=True,
                description="Notifications Gateway. Reads the org IDs subscribed to lifecycle reports.",
            )
        )

    if settings.kessel_enabled:
        kessel_host, kessel_port = _split_host_port(settings.kessel_url)
        if kessel_host:
            found.append(
                Destination(
                    purpose=PURPOSE_KESSEL,
                    host=kessel_host,
                    port=kessel_port,
                    protocol="grpc",
                    internet=False,
                    description="Kessel Inventory API. In-cluster workspace authorization.",
                )
            )

        oidc_host, oidc_port = _split_host_port(settings.kessel_auth_oidc_issuer)
        if oidc_host:
            found.append(
                Destination(
                    purpose=PURPOSE_KESSEL_OIDC,
                    host=oidc_host,
                    port=oidc_port or 443,
                    protocol="https",
                    internet=True,
                    description="SSO OIDC discovery and client-credentials token for Kessel.",
                )
            )

    sentry_host, sentry_port = _split_host_port(os.getenv("SENTRY_DSN"))
    if sentry_host:
        found.append(
            Destination(
                purpose=PURPOSE_SENTRY,
                host=sentry_host,
                port=sentry_port or 443,
                protocol="https",
                internet=True,
                description="Sentry error reporting. Connections are made by the Sentry SDK's own transport.",
            )
        )

    return found


def allowed_hosts(settings: Settings) -> frozenset[str]:
    """Return the hostnames this process may connect to."""
    return frozenset(destination.host for destination in destinations(settings))


class AuditedTransport(httpx.AsyncBaseTransport):
    """An httpx transport that records and allow-lists every request.

    Implemented as a transport rather than as httpx event hooks because hooks
    do not see transport-level failures. A connection that is refused, times
    out or fails TLS verification never produces a response, and those are
    exactly the outcomes worth alerting on.
    """

    def __init__(
        self,
        purpose: str,
        *,
        allowed: frozenset[str],
        enforce: bool,
        wrapped: httpx.AsyncBaseTransport | None = None,
        **transport_kwargs: t.Any,
    ) -> None:
        self._purpose = purpose
        self._allowed = allowed
        self._enforce = enforce
        self._wrapped = wrapped if wrapped is not None else httpx.AsyncHTTPTransport(**transport_kwargs)

    def _fields(self, request: httpx.Request) -> dict[str, t.Any]:
        # The path is kept but the query string is not: it carries filter
        # parameters and is where a token would leak into a log.
        return {
            "purpose": self._purpose,
            "dest_host": request.url.host,
            "dest_port": request.url.port or (443 if request.url.scheme == "https" else 80),
            "dest_scheme": request.url.scheme,
            "dest_path": request.url.path,
            "http_method": request.method,
            "direction": "egress",
        }

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        fields = self._fields(request)

        if request.url.host not in self._allowed:
            log_audit_event(
                ACTION_EGRESS_DENIED,
                RESULT_FAILURE,
                level="error",
                enforced=self._enforce,
                reason="not-in-allow-list",
                **fields,
            )
            if self._enforce:
                raise EgressNotAllowed(f"Egress to {request.url.host} is not in the allow list")

        start = time.perf_counter_ns()
        try:
            response = await self._wrapped.handle_async_request(request)
        except Exception as err:
            log_audit_event(
                ACTION_EGRESS,
                RESULT_FAILURE,
                level="error",
                duration=time.perf_counter_ns() - start,
                reason=type(err).__name__,
                **fields,
            )
            raise

        failed = response.status_code >= 400
        log_audit_event(
            ACTION_EGRESS,
            RESULT_FAILURE if failed else RESULT_SUCCESS,
            level="warning" if failed else "info",
            duration=time.perf_counter_ns() - start,
            status_code=response.status_code,
            **fields,
        )
        return response

    async def aclose(self) -> None:
        await self._wrapped.aclose()


def egress_client(purpose: str, settings: Settings, **client_kwargs: t.Any) -> httpx.AsyncClient:
    """Return an ``httpx.AsyncClient`` that logs and allow-lists its requests.

    Use this instead of constructing ``httpx.AsyncClient`` directly, so that no
    outbound call escapes the audit trail. ``verify`` is forwarded to the
    transport rather than the client, because a client-level ``verify`` is
    ignored once a custom transport is supplied.
    """
    verify = client_kwargs.pop("verify", True)

    return httpx.AsyncClient(
        transport=AuditedTransport(
            purpose,
            allowed=allowed_hosts(settings),
            enforce=settings.egress_enforce,
            verify=verify,
        ),
        **client_kwargs,
    )


def log_egress(purpose: str, settings: Settings, target: str, result: str, **fields: t.Any) -> None:
    """Record one outbound connection made outside of httpx.

    The Kessel gRPC channel and the SSO discovery call are made by the
    kessel-sdk, which does not accept an httpx transport. They are logged here
    at the point the connection is established instead, which is the
    granularity the control asks for -- gRPC holds one long-lived channel, so
    per-RPC events would say nothing further about the connection.
    """
    host, port = _split_host_port(target)
    log_audit_event(
        ACTION_EGRESS,
        result,
        level="info" if result == RESULT_SUCCESS else "error",
        purpose=purpose,
        dest_host=host,
        dest_port=port,
        direction="egress",
        allow_listed=host in allowed_hosts(settings),
        **fields,
    )
