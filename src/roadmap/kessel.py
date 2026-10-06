"""Kessel / RBAC v2 authorization helpers.

This module wraps the Kessel gRPC Inventory API and the RBAC v2 workspace
helpers from ``kessel-sdk``. It is only used when ``settings.kessel_enabled`` is
True; the default authorization path remains RBAC v1 (see
``roadmap.common.query_rbac``).

The one operation Digital Roadmap needs is enumerating the workspaces a user is
allowed to view hosts in (relation ``inventory_host_view``). Those workspace ids
are used directly as the host-group filter consumed by
``roadmap.common.query_host_inventory`` (each equals a host's groups[].id).

Reference implementations:
* RedHatInsights/advisor-backend (Python) -- api/kessel.py, api/permissions.py
* RedHatInsights/compliance-backend (Ruby) -- app/services/kessel_rbac.rb
"""

# The kessel-sdk package is not present in the shared CI type-check image, so
# pyright cannot resolve these imports there. It is a real, pinned runtime
# dependency (see requirements/requirements-*.txt); suppress the missing-import
# diagnostic for this module rather than weakening type checking globally.
# pyright: reportMissingImports=false

import logging
import time
import typing as t

import httpx
from fastapi import HTTPException
from kessel.auth import fetch_oidc_discovery
from kessel.auth import OAuth2ClientCredentials
from kessel.inventory.v1beta2 import ClientBuilder
from kessel.rbac.v2 import list_workspaces_async
from kessel.rbac.v2 import principal_subject

from roadmap.config import Settings


logger = logging.getLogger("uvicorn.error")

# The Kessel relation that grants viewing hosts within a workspace.
HOST_VIEW_RELATION = "inventory_host_view"

# Identity "type" -> the identity sub-object that carries "user_id".
# Systems have no user_id and cannot be turned into a principal subject.
_USER_ID_FIELD = {
    "User": "user",
    "ServiceAccount": "service_account",
}

# Module-level caches. The gRPC channel is expensive to build, so the client is
# memoized for the process lifetime. Cleared by reset_caches() in tests.
_client: t.Any = None

# Service account OAuth2 token cache for s2s HTTP auth (RBAC, etc.).
_sa_token: str | None = None
_sa_token_expires_at: float = 0


def reset_caches() -> None:
    """Reset module-level caches. Intended for use in tests."""
    global _client, _sa_token, _sa_token_expires_at
    _client = None
    _sa_token = None
    _sa_token_expires_at = 0


def get_service_account_token(settings: Settings) -> str | None:
    """Fetch an OAuth2 Bearer token for service-to-service authentication.

    Uses the Kessel service account credentials (client_id / client_secret)
    to perform an OAuth2 client-credentials grant against the OIDC token
    endpoint.  Tokens are cached in-process and refreshed 30 s before
    expiry.

    Returns ``None`` when Kessel auth is disabled or credentials are
    unavailable so callers can fall back to x-rh-identity passthrough.
    """
    global _sa_token, _sa_token_expires_at

    if not settings.kessel_auth_enabled:
        return None

    client_id = settings.kessel_auth_client_id
    client_secret = settings.kessel_auth_client_secret.get_secret_value()
    if not client_id or not client_secret:
        return None

    if _sa_token and time.time() < _sa_token_expires_at:
        return _sa_token

    try:
        discovery = fetch_oidc_discovery(settings.kessel_auth_oidc_issuer)
        with httpx.Client(timeout=10) as client:
            response = client.post(
                discovery.token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            _sa_token = token_data["access_token"]
            _sa_token_expires_at = time.time() + token_data.get("expires_in", 300) - 30
            return _sa_token
    except Exception as err:
        logger.warning("Failed to fetch service account token: %s", err)
        return None


def _build_credentials(settings: Settings) -> OAuth2ClientCredentials:
    discovery = fetch_oidc_discovery(settings.kessel_auth_oidc_issuer)
    return OAuth2ClientCredentials(
        client_id=settings.kessel_auth_client_id,
        client_secret=settings.kessel_auth_client_secret.get_secret_value(),
        token_endpoint=discovery.token_endpoint,
    )


def get_client(settings: Settings) -> t.Any:
    """Return a cached async Kessel Inventory gRPC stub, building it on first use."""
    global _client
    if _client is not None:
        return _client

    builder = ClientBuilder(settings.kessel_url)
    if settings.kessel_insecure:
        builder.insecure()
    elif settings.kessel_auth_enabled:
        builder.oauth2_client_authenticated(_build_credentials(settings))
    else:
        builder.unauthenticated()

    # build_async() returns an async stub that uses grpc.aio channels, which
    # integrate with the asyncio event loop. The sync build() sets
    # SingleThreadedUnaryStream which deadlocks when the calling thread is
    # the asyncio event loop (FastAPI runs async handlers on the loop).
    _client, _ = builder.build_async()
    logger.info("Built Kessel client (async)")
    return _client


def subject_from_identity(identity: dict[str, t.Any], domain: str) -> t.Any:
    """Build a Kessel principal SubjectReference from a decoded identity.

    Raise HTTPException(403) if the identity has no usable user_id (e.g. a
    System identity, or an unsupported type).
    """
    field = _USER_ID_FIELD.get(identity.get("type", ""))
    user_id = identity.get(field, {}).get("user_id") if field else None
    if not user_id:
        logger.warning("Cannot build Kessel subject: missing user_id for identity type %r", identity.get("type"))
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    return principal_subject(str(user_id), domain)


async def host_groups_for(client: t.Any, subject: t.Any) -> list[str]:
    """Return the workspace ids the subject may view hosts in.

    Enumerates workspaces via the Kessel Inventory ``StreamedListObjects`` API
    (pagination handled by the SDK) using the ``inventory_host_view`` relation.
    """
    responses = [r async for r in list_workspaces_async(client, subject, HOST_VIEW_RELATION)]
    return [response.object.resource_id for response in responses]
