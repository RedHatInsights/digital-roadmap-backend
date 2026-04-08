"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio
import os
import time

import structlog

from notificator.kafka import kafka_producer
from notificator.notificator import Notificator
from notificator.notificator_config import NotificatorSettings
from roadmap.custom_logging import setup_logging


settings = NotificatorSettings.create()
setup_logging(json_logs=settings.json_logging, log_level=settings.log_level)
logger = structlog.get_logger(__name__)

ORG_IDS = [int(os.environ.get("ORG_ID", "1234"))]


async def main():
    await lifecycle_notification()
    await roadmap_notification()


async def lifecycle_notification():
    failed_orgs = []
    async with kafka_producer() as producer:
        # TODO ORG_IDs will be received from API
        for org_id in ORG_IDS:
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

    if failed_orgs:
        raise RuntimeError(f"Lifecycle notification failed for {len(failed_orgs)}/{len(ORG_IDS)} orgs: {failed_orgs}")


async def roadmap_notification():
    pass


if __name__ == "__main__":
    asyncio.run(main())
