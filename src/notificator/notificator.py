from __future__ import annotations

import time

from datetime import datetime
from datetime import UTC
from uuid import uuid4

import structlog

from notificator.cache import CachedResult
from notificator.notificator_config import NotificatorSettings
from roadmap.common import query_host_inventory
from roadmap.database import get_db
from roadmap.models import SupportStatus
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream
from roadmap.v1.lifecycle.rhel import get_relevant_systems


logger = structlog.get_logger(__name__)


NOTIFY_STATUSES = {SupportStatus.retired, SupportStatus.near_retirement}


class Notificator:
    settings = NotificatorSettings.create()

    def __init__(self, org_id: int):
        self.org_id = org_id

    async def get_hosts(self):
        """Fetch hosts from HBI to be able to process relevant systems and appstreams.

        The HBI should be fetched only once for both because of the performance - there can be
        a huge block of systems registered into inventory and fetching that twice would be
        time consuming.
        """
        start_time = time.time()
        logger.info("Fetching hosts from inventory", org_id=self.org_id)

        async for session in get_db():
            async for result in query_host_inventory(
                org_id=str(self.org_id),
                session=session,
                settings=self.settings,
                host_groups=set(),  # unrestricted access, response for org_id can be requested
            ):
                hosts = [row async for row in result.mappings()]
                elapsed = time.time() - start_time
                logger.info(
                    "Fetched hosts from inventory",
                    org_id=self.org_id,
                    host_count=len(hosts),
                    duration_seconds=round(elapsed, 2),
                )
                return hosts

        logger.warning("No database session available", org_id=self.org_id)
        return []

    async def get_relevant_appstreams(
        self,
        hosts,
    ) -> dict[str, dict[str, dict[str, int]]]:
        """Get relevant appstreams based on response from HBI.

        Appstreams are filtered to include only ones with status specified in `NOTIFY_STATUSES`
        and aggregated into counts grouped by os_major.

        Each status is guaranteed to exist, the key contains the status name - e.g. "appstream_retired" or
        "appstream_near_retirement".
        """
        start_time = time.time()
        logger.info("Processing appstreams", org_id=self.org_id)

        relevant_appstreams = await systems_by_app_stream(
            org_id=str(self.org_id),
            systems=CachedResult(hosts),  # pyright: ignore [reportArgumentType]
        )

        appstreams_sections: dict[str, dict[str, dict[str, int]]] = {
            f"appstream_{status.name}": {} for status in NOTIFY_STATUSES
        }

        for app_stream, systems in relevant_appstreams.items():
            status = app_stream.app_stream_entity.support_status
            if status in NOTIFY_STATUSES:
                status_key = f"appstream_{status.name}"
                os_key = f"rhel{app_stream.app_stream_entity.os_major}"
                group = appstreams_sections[status_key].setdefault(os_key, {"count": 0, "systems_count": 0})
                group["count"] += 1
                group["systems_count"] += len(systems)

        # Ensure every status group has entries for all os_majors seen in any group
        # E.g. if RHEL9 appstream is present in `appstream_retired`, have it also in the `appstream_near_retirement`
        # Using for nested for loop there is safe, not much RHEL versions are expected.
        all_os_keys = {os_key for section in appstreams_sections.values() for os_key in section}
        for section in appstreams_sections.values():
            for os_key in all_os_keys:
                section.setdefault(os_key, {"count": 0, "systems_count": 0})

        elapsed = time.time() - start_time
        logger.info(
            "Processed appstreams",
            org_id=self.org_id,
            appstream_count=len(relevant_appstreams),
            duration_seconds=round(elapsed, 2),
        )
        return appstreams_sections

    async def get_relevant_rhel(self, hosts) -> dict[str, dict[str, int]]:
        """Get relevant RHEL versions based on response from HBI.

        RHEL versions are filtered to include only ones with status specified in `NOTIFY_STATUSES`
        and aggregated into counts.

        Each status is guaranteed to exist, the key contains the status name - e.g. "rhel_retired" or
        "rhel_near_retirement".
        """
        start_time = time.time()
        logger.info("Processing RHEL releases", org_id=self.org_id)

        relevant_systems = await get_relevant_systems(
            org_id=str(self.org_id),
            systems=CachedResult(hosts),  # pyright: ignore [reportArgumentType]
        )
        rhel_sections: dict[str, dict[str, int]] = {
            f"rhel_{status.name}": {"rhel_versions_count": 0, "systems_count": 0} for status in NOTIFY_STATUSES
        }
        for system in relevant_systems.data:
            if system.name != "RHEL":
                continue
            if system.support_status in NOTIFY_STATUSES:
                key = f"rhel_{system.support_status.name}"
                rhel_sections[key]["rhel_versions_count"] += 1
                rhel_sections[key]["systems_count"] += system.count

        elapsed = time.time() - start_time
        logger.info(
            "Processed RHEL systems",
            org_id=self.org_id,
            relevant_systems_count=len(relevant_systems.data),
            duration_seconds=round(elapsed, 2),
        )
        return rhel_sections

    async def get_lifecycle_notification(self) -> dict:
        """Gather required information for notification and build kafka message for notification backend."""
        logger.info("Building lifecycle notification", org_id=self.org_id)

        hosts = await self.get_hosts()
        rhel_grouped = await self.get_relevant_rhel(hosts)
        appstream_grouped = await self.get_relevant_appstreams(hosts)

        payload = _build_notification_payload(
            rhel_grouped=rhel_grouped,
            appstream_grouped=appstream_grouped,
            org_id=str(self.org_id),
            event_type="retiring-lifecycle-monthly-report",
        )

        logger.info("Built lifecycle notification", org_id=self.org_id, event_type="retiring-lifecycle-monthly-report")
        return payload


def _build_notification_payload(
    rhel_grouped: dict[str, dict[str, int]],
    appstream_grouped: dict[str, dict[str, dict[str, int]]],
    org_id: str,
    event_type: str,
    bundle: str = "rhel",
    application: str = "planning",
) -> dict:
    """Build kafka message for notification backend using their specified format.

    Returns::

        {
            "version": "v1.0.0",
            "id": "db6e6cee-...",
            "bundle": "rhel",
            "application": "planning",
            "event_type": "retiring-lifecycle-monthly-report",
            "timestamp": "2026-02-24T12:00:00Z",
            "org_id": "1234",
            "events": [{
                "metadata": {},
                "payload": {
                    "rhel_retired": {"rhel_versions_count": 6, "systems_count": 5},
                    "rhel_near_retirement": {"rhel_versions_count": 1, "systems_count": 3},
                    "appstream_retired": {
                        "rhel8": {"count": 2, "systems_count": 5},
                        "rhel9": {"count": 2, "systems_count": 8},
                    },
                    "appstream_near_retirement": {
                        "rhel8": {"count": 5, "systems_count": 7},
                        "rhel9": {"count": 22, "systems_count": 6},
                    },
                }
            }],
            "recipients": [],
        }
    """
    return {
        "version": "v1.0.0",
        "id": str(uuid4()),
        "bundle": bundle,
        "application": application,
        "event_type": event_type,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),  # or we can use datetime.now(UTC).isoformat()
        "org_id": org_id,
        "context": {},
        "events": [
            {
                "metadata": {},
                "payload": {**rhel_grouped, **appstream_grouped},
            },
        ],
        "recipients": [],
    }
