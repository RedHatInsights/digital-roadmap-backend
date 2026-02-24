from __future__ import annotations

from datetime import datetime
from datetime import UTC
from uuid import uuid4

from roadmap.common import query_host_inventory
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import SupportStatus
from roadmap.models import System
from roadmap.models import SystemInfo
from roadmap.v1.lifecycle.app_streams import AppStreamKey
from roadmap.v1.lifecycle.app_streams import RelevantAppStream
from roadmap.v1.lifecycle.app_streams import systems_by_app_stream
from roadmap.v1.lifecycle.rhel import get_relevant_systems


NOTIFY_STATUSES = {SupportStatus.retired, SupportStatus.near_retirement}


class CachedResult:
    """Wraps a list of row mappings to mimic AsyncResult.yield_per().mappings()."""

    def __init__(self, rows):
        self._rows = rows

    def yield_per(self, _n):
        return self

    def mappings(self):
        return self

    def __aiter__(self):
        return self._async_iter()

    async def _async_iter(self):
        for row in self._rows:
            yield row


def _build_rhel_section(rhel_systems: list[System]) -> dict:
    total = sum(s.count for s in rhel_systems)
    return {
        "meta": {"count": len(rhel_systems), "total": total},
        "data": [system.model_dump(mode="json") for system in rhel_systems],
    }


def _build_appstream_section(
    systems_by_stream: dict[AppStreamKey, set[SystemInfo]],
) -> dict:
    data = []
    total = 0
    for app_stream, systems in systems_by_stream.items():
        entity = app_stream.app_stream_entity
        count = len(systems)
        total += count
        relevant = RelevantAppStream(
            name=app_stream.name,
            display_name=entity.display_name,
            application_stream_name=entity.application_stream_name,
            application_stream_type=entity.application_stream_type,
            start_date=entity.start_date,
            end_date=entity.end_date,
            os_major=entity.os_major,
            os_minor=entity.os_minor,
            count=count,
            rolling=entity.rolling,
            systems_detail=systems,
            related=False,
        )
        data.append(relevant.model_dump(mode="json"))
    return {
        "meta": {"count": len(data), "total": total},
        "data": data,
    }


def build_notification_payload(
    rhel_systems: list[System],
    systems_by_stream: dict[AppStreamKey, set[SystemInfo]],
    org_id: str,
    *,
    bundle: str = "rhel",
    application: str = "digital-roadmap",
    event_type: str = "lifecycle-expiring-soon",
) -> dict:
    return {
        "version": "v1.1.0",
        "id": str(uuid4()),
        "bundle": bundle,
        "application": application,
        "event_type": event_type,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "org_id": org_id,
        "context": {},
        "events": [
            {
                "metadata": {},
                "payload": {
                    "rhel_systems_expiring_soon": _build_rhel_section(rhel_systems),
                    "appstream_packages_expiring_soon": _build_appstream_section(
                        systems_by_stream,
                    ),
                },
            },
        ],
        "recipients": [],
    }


class Notificator:
    settings = Settings.create()
    org_id: int | None = None

    async def get_hosts(self):
        async for session in get_db():
            async for result in query_host_inventory(
                org_id=str(self.org_id),
                session=session,
                settings=self.settings,
                host_groups=set(),  # unrestricted access
            ):
                return [row async for row in result.mappings()]

    async def get_relevant_appstreams(self, hosts):
        relevant_appstreams = await systems_by_app_stream(
            org_id=str(self.org_id),
            systems=CachedResult(hosts),  # pyright: ignore [reportArgumentType]
        )
        filtered = {}
        for app_stream, systems in relevant_appstreams.items():
            if app_stream.app_stream_entity.support_status in NOTIFY_STATUSES:
                filtered[app_stream] = systems
        return filtered

    async def get_relevant_rhel(self, hosts):
        relevant_systems = await get_relevant_systems(
            org_id=str(self.org_id),
            systems=CachedResult(hosts),  # pyright: ignore [reportArgumentType]
        )
        return [system for system in relevant_systems.data if system.support_status in NOTIFY_STATUSES]


if __name__ == "__main__":
    # PYTHONPATH=src python src/notificator/main.py

    import asyncio
    import json

    async def main():
        n = Notificator()
        n.org_id = 1234

        hosts = await n.get_hosts()

        systems_by_stream = await n.get_relevant_appstreams(hosts)
        rhel_systems = await n.get_relevant_rhel(hosts)

        payload = build_notification_payload(
            rhel_systems=rhel_systems,
            systems_by_stream=systems_by_stream or {},
            org_id=str(n.org_id),
        )
        print(json.dumps(payload, indent=2))  # noqa: T201

    asyncio.run(main())
