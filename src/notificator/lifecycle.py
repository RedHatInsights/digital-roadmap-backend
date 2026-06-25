import time

import structlog

from notificator.kafka import kafka_producer
from notificator.notificator import Notificator
from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION
from notificator.subscriptions import get_org_ids


logger = structlog.get_logger(__name__)


async def lifecycle_notification(override_org_ids: list[int] | None = None):
    logger.info("Started lifecycle notification")
    lifecycle_notification_start_time = time.time()
    try:
        org_ids = override_org_ids if override_org_ids is not None else await get_org_ids(LIFECYCLE_SUBSCRIPTION)
    except Exception:
        logger.exception("Failed to get org_ids for lifecycle notification, no orgs were notified.")
        return
    if not org_ids:
        logger.warning("No subscribed org IDs found, skipping lifecycle notification")
        return

    failed_orgs = []

    try:
        async with kafka_producer() as producer:
            for org_id in org_ids:
                start_time = time.time()
                logger.info("Processing lifecycle notification", org_id=org_id)
                try:
                    n = Notificator(org_id=org_id)
                    payload = await n.get_lifecycle_notification()
                    logger.debug("Payload generated", org_id=org_id, payload=payload)
                    await producer.send_notification(payload)
                    elapsed = time.time() - start_time
                    logger.info("Lifecycle notification completed", org_id=org_id, duration_seconds=round(elapsed, 2))
                # Wide exception, we don't want one failed ORG_ID causing failure of the whole script.
                except Exception:
                    elapsed = time.time() - start_time
                    logger.exception(
                        "Failed to process lifecycle notification", org_id=org_id, duration_seconds=round(elapsed, 2)
                    )
                    failed_orgs.append(org_id)
    except Exception:
        logger.exception("Failed to initialize Kafka producer for lifecycle notification, no orgs were notified.")
        return

    lifecycle_notification_elapsed = time.time() - lifecycle_notification_start_time
    logger.info(
        "Finished lifecycle notification",
        duration_seconds=lifecycle_notification_elapsed,
        processed_org_ids=len(org_ids),
    )

    if failed_orgs:
        logger.error(
            "Lifecycle notification failed for some orgs",
            failed_orgs=failed_orgs,
            failed_count=len(failed_orgs),
            total_count=len(org_ids),
        )
