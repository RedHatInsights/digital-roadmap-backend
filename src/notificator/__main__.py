"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio
import logging
import os

from notificator.kafka import kafka_producer
from notificator.notificator import Notificator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORG_IDS = [int(os.environ.get("ORG_ID", "1234"))]


async def main():
    await lifecycle_notification()
    await roadmap_notification()


async def lifecycle_notification():
    failed_orgs = []
    async with kafka_producer() as producer:
        # TODO ORG_IDs will be received from API
        for org_id in ORG_IDS:
            logger.info("Processing ORG_ID: %s", org_id)
            try:
                n = Notificator(org_id=org_id)
                payload = await n.get_lifecycle_notification()
                logger.debug("Payload: %s", payload)
                await producer.send_notification(payload)
            # Wide exception, we don't want one failed ORG_ID causing failure of the whole script.
            except Exception:
                logger.exception("Failed to process lifecycle notification for org_id=%s", org_id)
                failed_orgs.append(org_id)

    if failed_orgs:
        raise RuntimeError(f"Lifecycle notification failed for {len(failed_orgs)}/{len(ORG_IDS)} orgs: {failed_orgs}")


async def roadmap_notification():
    pass


if __name__ == "__main__":
    asyncio.run(main())
