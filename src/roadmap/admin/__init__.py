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


logger = structlog.get_logger(__name__)


async def require_internal_user(
    request: Request,
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
    settings: Settings = Depends(Settings.create),
) -> None:
    """Reject requests that do not come from a Red Hat internal user.

    The ``x-rh-identity`` header is injected by 3scale and contains a
    base64-encoded JSON blob. We check ``identity.user.is_internal == True``
    to restrict access to Red Hat associates only.

    The check is always on unless ``admin_auth_required`` is explicitly set to
    False. It used to be skipped whenever ``env_name != "prod"``. app-interface
    passes ENV_NAME per target, so it ran in production but not in stage, perf
    or ephemeral, where these routes answered unauthenticated requests. Tying
    an authorization decision to an environment's name also leaves it one
    app-interface edit away from switching off in production.

    ``is_internal`` is asserted by the caller-supplied header, so this guard is
    only as strong as the edge that overwrites that header. It is a defence in
    depth measure, not the trust boundary: the service must not be reachable
    without traversing the gateway.

    Every outcome is recorded as an event of interest. These routes are the
    privileged surface of the service, so Infosec wants both the administrative
    actions that succeed and the attempts that are turned away.
    """
    # The endpoint is the administrative action being attempted, and is what
    # distinguishes one admin event from another in Splunk.
    endpoint = f"{request.method} {request.url.path}"

    if not settings.admin_auth_required:
        # The internal-user check has been deliberately disabled, so say so in
        # the record rather than letting it look like a verified admin action.
        logger.warning(
            "Admin authorization is disabled; /admin is open to any caller that reaches this service",
            env_name=settings.env_name,
        )
        log_audit_event(ACTION_ADMIN, RESULT_SUCCESS, endpoint=endpoint, authorization="skipped-auth-disabled")
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
