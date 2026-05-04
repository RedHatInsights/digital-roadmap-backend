import structlog

from fastapi import APIRouter
from fastapi import HTTPException

from notificator.kafka import kafka_producer
from notificator.kafka import KafkaBrokersNotConfigured
from notificator.notificator import Notificator


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.put("/notificator", summary="Trigger lifecycle notification for an org")
async def trigger_notificator(
    org_id: int,
):
    logger.info("Admin trigger: lifecycle notification", org_id=org_id)

    try:
        n = Notificator(org_id=org_id)
        payload = await n.get_lifecycle_notification()
    except Exception as exc:
        logger.exception("Failed to build lifecycle notification", org_id=org_id)
        raise HTTPException(status_code=500, detail=f"Failed to build lifecycle notification for org {org_id}") from exc

    try:
        async with kafka_producer() as producer:
            await producer.send_notification(payload)
    except KafkaBrokersNotConfigured as exc:
        logger.error("Kafka brokers not configured", org_id=org_id)
        raise HTTPException(status_code=503, detail="Kafka brokers not configured") from exc
    except Exception as exc:
        logger.exception("Failed to send notification to Kafka", org_id=org_id)
        raise HTTPException(status_code=500, detail=f"Failed to send notification for org {org_id}") from exc

    logger.info("Admin trigger: lifecycle notification sent", org_id=org_id)
    return {"message": f"Lifecycle notification sent for org {org_id}"}
