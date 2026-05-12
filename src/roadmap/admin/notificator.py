import structlog

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Body
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from notificator.kafka import KafkaBrokersNotConfigured
from notificator.lifecycle import lifecycle_notification


logger = structlog.get_logger(__name__)

router = APIRouter()


class CustomNotificatorRequest(BaseModel):
    org_ids: int | list[int] = Field(
        description="A single org ID or a list of org IDs that should receive lifecycle notifications."
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
    confirm_all: bool = Field(
        default=False,
        description="Set to true to confirm notifications should be triggered for every org subscribed to receive this type of notification.",
    )


async def _trigger_lifecycle_notification(org_ids: list[int] | None = None):
    logger.info("Admin trigger: lifecycle notification", org_ids=org_ids, total_orgs=len(org_ids or []))
    try:
        await lifecycle_notification(override_org_ids=org_ids)
    except KafkaBrokersNotConfigured as exc:
        logger.error("Kafka brokers not configured")
        raise HTTPException(status_code=503, detail="Kafka brokers not configured") from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


async def _trigger_lifecycle_notification_background(org_ids: list[int] | None = None):
    try:
        await _trigger_lifecycle_notification(org_ids=org_ids)
    except Exception:
        logger.exception(
            "Admin trigger: Unexpected background lifecycle notification failure",
            org_ids=org_ids,
            total_orgs=len(org_ids or []),
        )


@router.post("/notificator/custom", summary="Trigger lifecycle notification for one or more orgs")
async def trigger_notificator_custom(payload: CustomNotificatorRequest = Body(...)):
    org_ids = [payload.org_ids] if isinstance(payload.org_ids, int) else payload.org_ids
    unique_org_ids = sorted(set(org_ids))
    await _trigger_lifecycle_notification(org_ids=unique_org_ids)
    return {"message": "Lifecycle notification completed", "requested_org_ids": unique_org_ids}


@router.post("/notificator/all", summary="Trigger lifecycle notification for all orgs", status_code=202)
async def trigger_notificator_all(background_tasks: BackgroundTasks, payload: AllNotificatorRequest = Body(...)):
    if not payload.confirm_all:
        raise HTTPException(
            status_code=400,
            detail="Set confirm_all=true to trigger notifications for all orgs.",
        )

    background_tasks.add_task(_trigger_lifecycle_notification_background)
    return {"message": "Lifecycle notification accepted"}
