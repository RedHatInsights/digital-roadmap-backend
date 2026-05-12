"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio

import structlog

from notificator.lifecycle import lifecycle_notification
from notificator.lifecycle import roadmap_notification
from notificator.notificator_config import NotificatorSettings
from roadmap.custom_logging import setup_logging


logger = structlog.get_logger(__name__)


def configure_logging():
    settings = NotificatorSettings.create()
    setup_logging(json_logs=settings.json_logging, log_level=settings.log_level)


async def main():
    await lifecycle_notification()
    await roadmap_notification()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
