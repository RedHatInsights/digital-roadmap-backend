"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio
import time

import structlog

from notificator.kafka import kafka_producer
from notificator.notificator import Notificator
from notificator.notificator_config import LIFECYCLE_SUBSCRIPTION
from notificator.notificator_config import NotificatorSettings
from notificator.subscriptions import get_org_ids
from roadmap.custom_logging import setup_logging


settings = NotificatorSettings.create()
setup_logging(json_logs=settings.json_logging, log_level=settings.log_level)
logger = structlog.get_logger(__name__)


async def main():
    await lifecycle_notification()
    await roadmap_notification()


async def lifecycle_notification(org_ids: list[int] | None = None):
    logger.info("Started lifecycle notification")
    lifecycle_notification_start_time = time.time()
    org_ids = await get_org_ids(LIFECYCLE_SUBSCRIPTION, org_ids=org_ids)
    if not org_ids:
        logger.warning("No subscribed org IDs found, skipping lifecycle notification")
        return

    failed_orgs = []

    async with kafka_producer() as producer:  # TODO handle (re-raise) exception from start_producer
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

    lifecycle_notification_elapsed = time.time() - lifecycle_notification_start_time
    logger.info(
        "Finished lifecycle notification",
        duration_seconds=lifecycle_notification_elapsed,
        processed_org_ids=len(org_ids),
    )

    if failed_orgs:
        raise RuntimeError(f"Lifecycle notification failed for {len(failed_orgs)}/{len(org_ids)} orgs: {failed_orgs}")


async def roadmap_notification():
    pass


if __name__ == "__main__":
    asyncio.run(main())
