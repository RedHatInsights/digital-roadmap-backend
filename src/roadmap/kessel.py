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
import typing as t

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

# Module-level cache. The gRPC channel is expensive to build, so the client is
# memoized for the process lifetime. Cleared by reset_caches() in tests.
_client: t.Any = None


def reset_caches() -> None:
    """Reset module-level caches. Intended for use in tests."""
    global _client
    _client = None


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
