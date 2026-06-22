from __future__ import annotations

import time

from collections import Counter
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from uuid import uuid4

import structlog

from notificator.cache import CachedResult
from notificator.notificator_config import NotificatorSettings
from roadmap.common import query_host_inventory
from roadmap.database import get_db
from roadmap.models import SupportStatus
from roadmap.models import SystemInfo
from roadmap.v1 import upcoming
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream
from roadmap.v1.lifecycle.rhel import get_relevant_systems


logger = structlog.get_logger(__name__)


NOTIFY_STATUSES = {SupportStatus.retired, SupportStatus.near_retirement}


class Notificator:
    def __init__(self, org_id: int):
        self.org_id = org_id
        self.settings = NotificatorSettings.create()

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

        Appstreams with status in `NOTIFY_STATUSES` are aggregated into counts grouped
        by os_major.  Appstreams with other statuses (e.g. supported) are not counted,
        but their os_major is still tracked so that every OS major that has *any*
        appstream gets a zero-count entry in every section.

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
        # Track unique systems per (status, os_major) group separately — a single system
        # can appear in multiple appstreams, so naive len() summing would over-count.
        unique_systems: dict[str, dict[str, set[SystemInfo]]] = {
            f"appstream_{status.name}": {} for status in NOTIFY_STATUSES
        }
        all_os_keys: set[str] = set()

        for app_stream, systems in relevant_appstreams.items():
            os_key = f"rhel{app_stream.app_stream_entity.os_major}"
            all_os_keys.add(os_key)

            status = app_stream.app_stream_entity.support_status
            if status in NOTIFY_STATUSES:
                status_key = f"appstream_{status.name}"
                appstreams_sections[status_key].setdefault(os_key, {"count": 0, "systems_count": 0})
                appstreams_sections[status_key][os_key]["count"] += 1
                unique_systems[status_key].setdefault(os_key, set()).update(systems)

        # Resolve unique system sets into final integer counts
        for status_key, os_groups in unique_systems.items():
            for os_key, systems_set in os_groups.items():
                appstreams_sections[status_key][os_key]["systems_count"] = len(systems_set)

        # Ensure every status group has entries for all os_majors seen in any appstream
        # (including supported ones), so the consumer always gets a consistent shape.
        # Using a nested for loop here is safe; not many RHEL versions are expected.
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

        payload = _build_lifecycle_notification_payload(
            rhel_grouped=rhel_grouped,
            appstream_grouped=appstream_grouped,
            org_id=str(self.org_id),
            event_type="retiring-lifecycle-monthly-report",
            application="life-cycle",
        )

        logger.info("Built lifecycle notification", org_id=self.org_id, event_type="retiring-lifecycle-monthly-report")
        return payload

    async def get_relevant_upcoming(self, hosts) -> Counter[str]:
        """Get upcoming changes added within the last-month-to-date window.

        Calls the same logic as the ``/relevant/upcoming-changes`` endpoint but
        further filters to items whose ``dateAdded`` falls between the 1st of
        the previous month and today (inclusive).

        Returns a Counter keyed by ``UpcomingType`` value (addition, change,
        deprecation, enhancement).  Merging enhancement into addition is done
        at payload-build time so the raw counts stay separable.

        Example::

            Counter({"addition": 5, "deprecation": 2, "change": 1, "enhancement": 3})
        """
        start_time = time.time()
        logger.info("Processing upcoming changes", org_id=self.org_id)

        pkgs_by_system = await upcoming.packages_by_system(
            org_id=str(self.org_id),
            systems=CachedResult(hosts),  # pyright: ignore [reportArgumentType]
        )

        upcoming_with_hosts = upcoming.get_upcoming_data_with_hosts(
            packages_by_system=pkgs_by_system,
            settings=self.settings,
        )

        today = datetime.now(UTC).date()
        cutoff = _upcoming_cutoff_date(today)
        counts: Counter[str] = Counter()

        for item in upcoming_with_hosts:
            if item.details.deployedDate is None:
                # Item was not released yet, let's use today's date for testing
                # Shouldn't happen in production, meant mainly for staging
                logger.info(
                    f"{item.name} was not yet deployed, added to roadmap on {item.details.dateAdded}. Using today's date."
                )
                item.details.deployedDate = today
            if cutoff <= item.details.deployedDate <= today:
                counts[item.type] += 1

        elapsed = time.time() - start_time
        logger.info(
            "Processed upcoming changes",
            org_id=self.org_id,
            counts=dict(counts),
            cutoff_date=str(cutoff),
            duration_seconds=round(elapsed, 2),
        )
        return counts

    async def get_roadmap_notification(self) -> dict:
        """Gather required information for notification and build kafka message for notification backend."""
        logger.info("Building roadmap notification", org_id=self.org_id)

        hosts = await self.get_hosts()
        upcoming_counts = await self.get_relevant_upcoming(hosts)

        payload = _build_roadmap_notification_payload(
            upcoming_counts=upcoming_counts,
            org_id=str(self.org_id),
        )

        logger.info("Built roadmap notification", org_id=self.org_id, event_type="roadmap-monthly-report")
        return payload


def _upcoming_cutoff_date(reference_date: date) -> date:
    """Return the first day of the previous month (start of the reporting window).

    The reporting window spans from the 1st of the previous month to today,
    e.g. if today is May 2 the cutoff is April 1.
    """
    first_of_this_month = reference_date.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    return last_of_prev_month.replace(day=1)


def _build_roadmap_notification_payload(
    upcoming_counts: Counter[str],
    org_id: str,
    bundle: str = "rhel",
    application: str = "roadmap",
    event_type: str = "roadmap-monthly-report",
) -> dict:
    """Build kafka message for roadmap notification backend using their specified format.

    ``enhancement`` counts are folded into ``addition`` for the payload.

    Returns::

        {
            "version": "v1.0.0",
            "id": "63961201-...",
            "bundle": "rhel",
            "application": "roadmap",
            "event_type": "roadmap-monthly-report",
            "timestamp": "2026-04-15T15:50:05Z",
            "org_id": "1234",
            "context": {
                "roadmap": {
                    "report_date": "April 2026"
                }
            },
            "events": [{
                "metadata": {},
                "payload": {
                    "addition": {"count": 4},
                    "deprecation": {"count": 5},
                    "change": {"count": 0},
                }
            }],
            "recipients": [],
        }
    """
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    first_of_this_month = now.date().replace(day=1)
    previous_month = first_of_this_month - timedelta(days=1)
    report_date = previous_month.strftime("%B %Y")

    payload_counts = {
        "addition": upcoming_counts["addition"] + upcoming_counts["enhancement"],
        "deprecation": upcoming_counts["deprecation"],
        "change": upcoming_counts["change"],
    }

    return {
        "version": "v1.0.0",
        "id": str(uuid4()),
        "bundle": bundle,
        "application": application,
        "event_type": event_type,
        "timestamp": timestamp,
        "org_id": org_id,
        "context": {
            application: {
                "report_date": report_date,
            }
        },
        "events": [
            {
                "metadata": {},
                "payload": {type_key: {"count": count} for type_key, count in payload_counts.items()},
            },
        ],
        "recipients": [],
    }


def _build_lifecycle_notification_payload(
    rhel_grouped: dict[str, dict[str, int]],
    appstream_grouped: dict[str, dict[str, dict[str, int]]],
    org_id: str,
    event_type: str,
    bundle: str = "rhel",
    application: str = "life-cycle",
) -> dict:
    """Build kafka message for notification backend using their specified format.

    Returns::

        {
            "version": "v1.0.0",
            "id": "db6e6cee-...",
            "bundle": "rhel",
            "application": "life-cycle",
            "event_type": "retiring-lifecycle-monthly-report",
            "timestamp": "2026-02-24T12:00:00Z",
            "org_id": "1234",
            "context": {
                "lifecycle": {
                    "report_date": "February 2026"
                }
            },
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
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    report_date = now.strftime("%B %Y")  # e.g., "May 2026"

    return {
        "version": "v1.0.0",
        "id": str(uuid4()),
        "bundle": bundle,
        "application": application,
        "event_type": event_type,
        "timestamp": timestamp,
        "org_id": org_id,
        "context": {
            application.replace("-", ""): {
                "report_date": report_date,
            }
        },
        "events": [
            {
                "metadata": {},
                "payload": {**rhel_grouped, **appstream_grouped},
            },
        ],
        "recipients": [],
    }
