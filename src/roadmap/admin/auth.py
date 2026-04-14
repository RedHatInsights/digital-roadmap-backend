from __future__ import annotations

import base64
import json
import typing as t

import structlog

from fastapi import Header
from fastapi import HTTPException


logger = structlog.get_logger(__name__)


async def require_associate(
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> dict:
    """Verify that the caller is a Red Hat associate (internal staff).

    Admin endpoints are only accessible through internal.console.redhat.com,
    which routes through Turnpike and injects a trusted x-rh-identity header
    with ``identity.type == "Associate"``.

    This dependency enforces that check at the application level as
    defense-in-depth, matching the pattern used by patchman-engine and
    vulnerability-engine admin APIs.

    See Also:
        https://github.com/RedHatInsights/identity-schemas/blob/main/3scale/identities/basic.json
        https://github.com/RedHatInsights/turnpike
    """
    if x_rh_identity is None:
        raise HTTPException(status_code=401, detail="Missing x-rh-identity header")

    try:
        decoded = base64.b64decode(x_rh_identity).decode("utf-8")
        id_header = json.loads(decoded)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid x-rh-identity header") from exc

    identity = id_header.get("identity", {})

    if identity.get("type", "").lower() != "associate":
        raise HTTPException(status_code=401, detail="Admin API requires associate identity")

    email = identity.get("associate", {}).get("email")
    logger.info("Admin API accessed", associate_email=email)

    return identity
