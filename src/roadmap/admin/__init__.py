"""Admin API endpoints.

All routes under ``/admin`` require the caller to be a Red Hat internal user
(validated via the ``x-rh-identity`` header in production). Sub-routers for
individual admin features are mounted here.
"""

import base64
import json
import typing as t

import structlog

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException

from roadmap.config import Settings

from .notifications import lifecycle
from .notifications import roadmap


logger = structlog.get_logger(__name__)


async def require_internal_user(
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    settings: Settings = Depends(Settings.create),
) -> None:
    """Reject requests that do not come from a Red Hat internal user.

    The ``x-rh-identity`` header is injected by 3scale and contains a
    base64-encoded JSON blob. We check ``identity.user.is_internal == True``
    to restrict access to Red Hat associates only.

    The check is always on unless ``admin_auth_required`` is explicitly set to
    False. It used to be skipped whenever ``env_name != "prod"``, which meant
    it was inert in every environment whose Clowder name was not the bare
    string "prod" -- leaving the notification triggers, which send real email
    to every subscribed org, open to unauthenticated callers.

    ``is_internal`` is asserted by the caller-supplied header, so this guard is
    only as strong as the edge that overwrites that header. It is a defence in
    depth measure, not the trust boundary: the service must not be reachable
    without traversing 3scale.
    """
    if not settings.admin_auth_required:
        logger.warning(
            "Admin authorization is disabled; /admin is open to any caller that reaches this service",
            env_name=settings.env_name,
        )
        return

    if x_rh_identity is None:
        logger.warning("Admin access denied: no identity header", reason="missing_identity")
        raise HTTPException(status_code=401, detail="Missing x-rh-identity header")

    try:
        payload = json.loads(base64.b64decode(x_rh_identity))
        user = payload.get("identity", {}).get("user") or {}
    except Exception as exc:
        logger.warning("Admin access denied: malformed identity header", reason="invalid_identity")
        raise HTTPException(status_code=401, detail="Invalid x-rh-identity header") from exc

    if not user.get("is_internal", False):
        logger.warning(
            "Admin access denied: caller is not an internal user",
            reason="not_internal",
            org_id=payload.get("identity", {}).get("org_id"),
        )
        raise HTTPException(status_code=403, detail="Admin endpoints are restricted to internal users")


router = APIRouter(
    prefix="/admin", tags=["Admin"], include_in_schema=False, dependencies=[Depends(require_internal_user)]
)
router.include_router(lifecycle.router)
router.include_router(roadmap.router)
