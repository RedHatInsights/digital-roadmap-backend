"""DEVELOPMENT:

Run using: PYTHONPATH=src python -m notificator.main"""

import asyncio
import json

from notificator.notificator import Notificator


async def main():
    # get_org_ids to notificy
    n = Notificator(org_id=1234)
    payload = await n.get_notification()
    print(json.dumps(payload, indent=2))  # noqa: T201
    # send payload to notification backend


if __name__ == "__main__":
    asyncio.run(main())
