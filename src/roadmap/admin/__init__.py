"""Admin API endpoints.

All routes under ``/admin`` require the caller to be a Red Hat internal user
(validated via the ``x-rh-identity`` header in production). Sub-routers for
individual admin features are mounted here.
"""

import base64
import json
import typing as t

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException

from roadmap.config import Settings

from .notifications import lifecycle
from .notifications import roadmap


async def require_internal_user(
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    settings: Settings = Depends(Settings.create),
) -> None:
    """Reject requests that do not come from a Red Hat internal user.

    The ``x-rh-identity`` header is injected by 3scale and contains a
    base64-encoded JSON blob.  We check
    ``identity.user.is_internal == True`` to restrict access to Red Hat
    associates only.

    In non-production environments the check is skipped.
    """
    if settings.env_name != "prod":
        return

    if x_rh_identity is None:
        raise HTTPException(status_code=401, detail="Missing x-rh-identity header")

    try:
        payload = json.loads(base64.b64decode(x_rh_identity))
        user = payload.get("identity", {}).get("user") or {}
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid x-rh-identity header") from exc

    if not user.get("is_internal", False):
        raise HTTPException(status_code=403, detail="Admin endpoints are restricted to internal users")


router = APIRouter(
    prefix="/admin", tags=["Admin"], include_in_schema=False, dependencies=[Depends(require_internal_user)]
)
router.include_router(lifecycle.router)
router.include_router(roadmap.router)
