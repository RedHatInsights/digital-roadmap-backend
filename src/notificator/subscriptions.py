"""Fetch subscribed org IDs from the Notifications Gateway using mTLS."""

from __future__ import annotations

import ssl

import httpx
import structlog

from notificator.notificator_config import DEV_ORG_IDS
from notificator.notificator_config import NotificatorSettings
from notificator.notificator_config import SubscriptionType


logger = structlog.get_logger(__name__)


async def get_org_ids(subscription: SubscriptionType) -> list[int]:
    """Resolve org IDs for a given subscription type.

    Precedence:
    1. Dev mode (``ROADMAP_DEV=1``) -> ``DEV_ORG_IDS``
    2. Subscription API fetch using mTLS
    """
    settings = NotificatorSettings.create()

    if settings.dev:
        logger.info("Dev mode: using hardcoded org IDs", org_ids=DEV_ORG_IDS)
        return list(DEV_ORG_IDS)

    return await fetch_subscribed_org_ids(settings, subscription)


async def fetch_subscribed_org_ids(settings: NotificatorSettings, subscription: SubscriptionType) -> list[int]:
    """Return org IDs subscribed to *subscription*.

    Calls the Notifications Gateway mTLS endpoint and extracts org IDs from
    the JSON response keyed by the subscription's event type.

    Raises ``httpx.HTTPStatusError`` on non-2xx responses.
    """
    if settings.subscriptions_url is None:
        raise RuntimeError("ROADMAP_SUBSCRIPTIONS_URL is not configured")

    url = f"{settings.subscriptions_url}/{subscription.application}"

    ctx = ssl.create_default_context()
    ctx.load_cert_chain(certfile=settings.tls_cert_path, keyfile=settings.tls_key_path)

    logger.info("Fetching subscribed org IDs", url=url, event_type=subscription.event_type)

    async with httpx.AsyncClient(verify=ctx, timeout=180) as client:
        response = await client.get(url, params={"eventTypeNames": subscription.event_type})
        response.raise_for_status()
        data = response.json()

    raw_ids = data.get(subscription.event_type, [])
    try:
        org_ids = [int(org_id) for org_id in raw_ids]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid subscriptions payload for event_type={subscription.event_type!r}; "
            f"expected list of ints, got {raw_ids!r}"
        ) from err

    logger.info("Fetched subscribed org IDs", count=len(org_ids), org_ids=org_ids)
    return org_ids
