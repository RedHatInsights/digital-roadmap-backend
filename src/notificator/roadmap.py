import time

import structlog

from notificator.kafka import kafka_producer
from notificator.notificator import Notificator
from notificator.notificator_config import ROADMAP_SUBSCRIPTION
from notificator.subscriptions import get_org_ids


logger = structlog.get_logger(__name__)


async def roadmap_notification(override_org_ids: list[int] | None = None, *, dry_run: bool = False):
    logger.info("Started roadmap notification", dry_run=dry_run)
    roadmap_notification_start_time = time.time()
    try:
        org_ids = override_org_ids if override_org_ids is not None else await get_org_ids(ROADMAP_SUBSCRIPTION)
    except Exception:
        logger.exception("Failed to get org_ids for roadmap notification, no orgs were notified.")
        return
    if not org_ids:
        logger.warning("No subscribed org IDs found, skipping roadmap notification")
        return

    failed_orgs = []

    try:
        async with kafka_producer() as producer:
            for org_id in org_ids:
                start_time = time.time()
                logger.info("Processing roadmap notification", org_id=org_id)
                try:
                    n = Notificator(org_id=org_id)
                    payload = await n.get_roadmap_notification()
                    logger.debug("Payload generated", org_id=org_id, payload=payload)
                    if dry_run:
                        logger.info("Dry run: skipping send", org_id=org_id, payload=payload)
                    else:
                        await producer.send_notification(payload)
                    elapsed = time.time() - start_time
                    logger.info("Roadmap notification completed", org_id=org_id, duration_seconds=round(elapsed, 2))
                # Wide exception, we don't want one failed ORG_ID causing failure of the whole script.
                except Exception:
                    elapsed = time.time() - start_time
                    logger.exception(
                        "Failed to process roadmap notification", org_id=org_id, duration_seconds=round(elapsed, 2)
                    )
                    failed_orgs.append(org_id)
    except Exception:
        logger.exception("Failed to get kafka producer for roadmap notification, no orgs were notified.")
        return

    roadmap_notification_elapsed = time.time() - roadmap_notification_start_time
    logger.info(
        "Finished roadmap notification",
        duration_seconds=roadmap_notification_elapsed,
        processed_org_ids=len(org_ids),
        dry_run=dry_run,
    )

    if failed_orgs:
        logger.error(
            "Roadmap notification failed for some orgs",
            failed_orgs=failed_orgs,
            failed_count=len(failed_orgs),
            total_count=len(org_ids),
        )
