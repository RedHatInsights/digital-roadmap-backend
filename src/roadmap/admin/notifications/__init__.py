"""Shared building blocks for admin notification endpoints.

Provides ``build_notification_router``, a factory that generates a set of
FastAPI routes (subscribed-orgs, custom trigger, and broadcast trigger) for
any notification type described by a ``NotificationKind``.
"""

from collections.abc import Callable
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

import structlog

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Body
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from notificator.kafka import KafkaBrokersNotConfigured
from notificator.notificator_config import SubscriptionType
from notificator.subscriptions import get_org_ids


logger = structlog.get_logger(__name__)

NotificationFunc = Callable[..., Coroutine[Any, Any, None]]


class CustomNotificatorRequest(BaseModel):
    """Request body for triggering notifications for specific orgs."""

    org_ids: int | list[int] = Field(
        description="A single org ID or a list of org IDs that should receive notifications."
    )

    @field_validator("org_ids")
    @classmethod
    def _validate_org_ids(cls, value: int | list[int]) -> int | list[int]:
        ids = [value] if isinstance(value, int) else value
        if not ids:
            raise ValueError("org_ids must contain at least one org ID")
        if any(org_id <= 0 for org_id in ids):
            raise ValueError("All org IDs must be positive integers")
        return value


class AllNotificatorRequest(BaseModel):
    """Request body for triggering notifications for all subscribed orgs."""

    confirm_all: bool = Field(
        default=False,
        description="Set to true to confirm notifications should be triggered for every org subscribed to receive this type of notification.",
    )


@dataclass
class NotificationKind:
    """Describes a notification type for the admin endpoint factory.

    ``label`` is used in route paths and log/response messages.
    ``subscription`` identifies the Notifications Gateway subscription.
    ``send`` is the async callable that actually dispatches notifications.
    """

    label: str
    subscription: SubscriptionType
    send: NotificationFunc


def build_notification_router(kind: NotificationKind) -> APIRouter:
    """Create a FastAPI router with admin endpoints for the given notification type.

    Generates three routes: ``subscribed-orgs`` (GET), ``custom`` (POST),
    and ``all`` (POST, background).
    """
    router = APIRouter()
    prefix = f"/notifications/{kind.label}"

    async def _trigger(org_ids: list[int] | None = None):
        logger.info(f"Admin trigger: {kind.label} notification", org_ids=org_ids, total_orgs=len(org_ids or []))
        try:
            await kind.send(override_org_ids=org_ids)
        except KafkaBrokersNotConfigured as exc:
            logger.error("Kafka brokers not configured")
            raise HTTPException(status_code=503, detail="Kafka brokers not configured") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    async def _trigger_background(org_ids: list[int] | None = None):
        try:
            await _trigger(org_ids=org_ids)
        except Exception as exc:
            logger.exception(
                f"Admin trigger: Unexpected background {kind.label} notification failure",
                org_ids=org_ids,
                total_orgs=len(org_ids or []),
                error=str(exc),
                error_type=type(exc).__name__,
            )

    @router.get(f"{prefix}/subscribed-orgs", summary=f"List orgs subscribed to {kind.label} notifications")
    async def get_subscribed_orgs():
        try:
            org_ids = await get_org_ids(kind.subscription)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Failed to fetch subscribed org IDs")
            raise HTTPException(status_code=500, detail="Failed to fetch subscribed org IDs") from exc
        return {"org_ids": org_ids, "count": len(org_ids)}

    @router.post(f"{prefix}/custom", summary=f"Trigger {kind.label} notification for one or more orgs")
    async def trigger_custom(payload: CustomNotificatorRequest = Body(...)):
        org_ids = [payload.org_ids] if isinstance(payload.org_ids, int) else payload.org_ids
        unique_org_ids = sorted(set(org_ids))
        await _trigger(org_ids=unique_org_ids)
        return {"message": f"{kind.label.capitalize()} notification completed", "requested_org_ids": unique_org_ids}

    @router.post(f"{prefix}/all", summary=f"Trigger {kind.label} notification for all orgs", status_code=202)
    async def trigger_all(background_tasks: BackgroundTasks, payload: AllNotificatorRequest = Body(...)):
        if not payload.confirm_all:
            raise HTTPException(
                status_code=400,
                detail="Set confirm_all=true to trigger notifications for all orgs.",
            )
        background_tasks.add_task(_trigger_background)
        return {"message": f"{kind.label.capitalize()} notification accepted"}

    return router
