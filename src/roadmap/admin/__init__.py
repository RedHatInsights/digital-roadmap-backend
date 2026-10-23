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
from fastapi import Request

from roadmap.audit import ACTION_ADMIN
from roadmap.audit import ACTION_AUTHN
from roadmap.audit import ACTION_AUTHZ
from roadmap.audit import log_audit_event
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
from roadmap.config import Settings

from .notifications import lifecycle
from .notifications import roadmap


async def require_internal_user(
    request: Request,
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    settings: Settings = Depends(Settings.create),
) -> None:
    """Reject requests that do not come from a Red Hat internal user.

    The ``x-rh-identity`` header is injected by 3scale and contains a
    base64-encoded JSON blob.  We check
    ``identity.user.is_internal == True`` to restrict access to Red Hat
    associates only.

    In non-production environments the check is skipped.

    Every outcome is recorded as an event of interest. These routes are the
    privileged surface of the service, so Infosec wants both the administrative
    actions that succeed and the attempts that are turned away.
    """
    # The endpoint is the administrative action being attempted, and is what
    # distinguishes one admin event from another in Splunk.
    endpoint = f"{request.method} {request.url.path}"

    if settings.env_name != "prod":
        # The internal-user check does not run outside production, so say so in
        # the record rather than letting it look like a verified admin action.
        log_audit_event(ACTION_ADMIN, RESULT_SUCCESS, endpoint=endpoint, authorization="skipped-non-prod")
        return

    if x_rh_identity is None:
        log_audit_event(
            ACTION_AUTHN, RESULT_FAILURE, level="warning", endpoint=endpoint, error_code=401, reason="missing-identity"
        )
        raise HTTPException(status_code=401, detail="Missing x-rh-identity header")

    try:
        payload = json.loads(base64.b64decode(x_rh_identity))
        user = payload.get("identity", {}).get("user") or {}
    except Exception as exc:
        log_audit_event(
            ACTION_AUTHN, RESULT_FAILURE, level="warning", endpoint=endpoint, error_code=401, reason="invalid-identity"
        )
        raise HTTPException(status_code=401, detail="Invalid x-rh-identity header") from exc

    if not user.get("is_internal", False):
        log_audit_event(
            ACTION_AUTHZ, RESULT_FAILURE, level="warning", endpoint=endpoint, error_code=403, reason="not-internal"
        )
        raise HTTPException(status_code=403, detail="Admin endpoints are restricted to internal users")

    log_audit_event(ACTION_ADMIN, RESULT_SUCCESS, endpoint=endpoint, authorization="internal-user")


router = APIRouter(
    prefix="/admin", tags=["Admin"], include_in_schema=False, dependencies=[Depends(require_internal_user)]
)
router.include_router(lifecycle.router)
router.include_router(roadmap.router)
