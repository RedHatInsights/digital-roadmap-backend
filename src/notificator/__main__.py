"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio

import structlog

from notificator.lifecycle import lifecycle_notification
from notificator.notificator_config import NotificatorSettings
from notificator.roadmap import roadmap_notification
from roadmap.audit import ACTION_SHUTDOWN
from roadmap.audit import ACTION_STARTUP
from roadmap.audit import log_audit_event
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
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

    # This job reads every subscribed org's hosts, so its start and finish are
    # recorded as events of interest the same way the API's are. A failed run
    # is recorded too: a run that stops early is a gap in the data access
    # records the rest of this job emits.
    log_audit_event(ACTION_STARTUP, RESULT_SUCCESS, component="notificator")
    try:
        asyncio.run(main())
    except BaseException as err:
        log_audit_event(
            ACTION_SHUTDOWN, RESULT_FAILURE, level="error", component="notificator", reason=type(err).__name__
        )
        raise

    log_audit_event(ACTION_SHUTDOWN, RESULT_SUCCESS, component="notificator")
