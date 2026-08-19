"""Kessel / RBAC v2 authorization helpers.

This module wraps the Kessel gRPC Inventory API and the RBAC v2 workspace
helpers from ``kessel-sdk``. It is only used when ``settings.kessel_enabled`` is
True; the default authorization path remains RBAC v1 (see
``roadmap.common.query_rbac``).

The one operation Digital Roadmap needs is enumerating the workspaces a user is
allowed to view hosts in (relation ``inventory_host_view``). Those workspace ids
are then mapped to the ``set[str | None]`` host-group filter consumed by
``roadmap.common.query_host_inventory``.

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
from kessel.auth import oauth2_auth_request
from kessel.auth import OAuth2ClientCredentials
from kessel.inventory.v1beta2 import ClientBuilder
from kessel.rbac.v2 import fetch_default_workspace
from kessel.rbac.v2 import fetch_root_workspace
from kessel.rbac.v2 import list_workspaces
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

# Module-level caches. The gRPC channel is expensive to build, and the org's
# root/default workspace ids are stable, so both are memoized for the process
# lifetime. Cleared by reset_caches() in tests.
_client: t.Any = None
_rbac_auth: t.Any = None
_org_wide_workspace_ids: dict[str, frozenset[str]] = {}


def reset_caches() -> None:
    """Reset module-level caches. Intended for use in tests."""
    global _client, _rbac_auth
    _client = None
    _rbac_auth = None
    _org_wide_workspace_ids.clear()


def _build_credentials(settings: Settings) -> OAuth2ClientCredentials:
    discovery = fetch_oidc_discovery(settings.kessel_auth_oidc_issuer)
    return OAuth2ClientCredentials(
        client_id=settings.kessel_auth_client_id,
        client_secret=settings.kessel_auth_client_secret.get_secret_value(),
        token_endpoint=discovery.token_endpoint,
    )


def get_client(settings: Settings) -> t.Any:
    """Return a cached Kessel Inventory gRPC stub, building it on first use."""
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

    # build() returns (stub, channel); we only need the stub.
    _client, _ = builder.build()
    # Do not log settings.kessel_url; it may reveal an internal hostname/IP.
    logger.info("Built Kessel client")
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


def host_groups_for(client: t.Any, subject: t.Any) -> list[str]:
    """Return the workspace ids the subject may view hosts in.

    Enumerates workspaces via the Kessel Inventory ``StreamedListObjects`` API
    (pagination handled by the SDK) using the ``inventory_host_view`` relation.
    """
    return [response.object.resource_id for response in list_workspaces(client, subject, HOST_VIEW_RELATION)]


def _auth_for_rbac(settings: Settings) -> t.Any:
    """Service-account auth used for RBAC v2 REST calls (fetch_*_workspace)."""
    global _rbac_auth
    if _rbac_auth is None:
        _rbac_auth = oauth2_auth_request(_build_credentials(settings))
    return _rbac_auth


def org_wide_workspace_ids(settings: Settings, org_id: str) -> frozenset[str]:
    """Return the org's root and default workspace ids (cached per org).

    A user granted ``inventory_host_view`` on either of these workspaces is an
    org-wide reader, which maps to unrestricted access.
    """
    if org_id in _org_wide_workspace_ids:
        return _org_wide_workspace_ids[org_id]

    auth = _auth_for_rbac(settings)
    root = fetch_root_workspace(settings.rbac_url, org_id, auth=auth)
    default = fetch_default_workspace(settings.rbac_url, org_id, auth=auth)
    ids = frozenset(ws_id for ws_id in (root.id, default.id) if ws_id)
    _org_wide_workspace_ids[org_id] = ids
    return ids
