"""Run using: PYTHONPATH=src python -m notificator"""

import asyncio
import json
import os

from notificator.notificator import Notificator


ORG_ID = int(os.environ.get("ORG_ID", "1234"))


async def main():
    n = Notificator(org_id=ORG_ID)
    payload = await n.get_notification()
    print(json.dumps(payload, indent=2))  # noqa: T201


asyncio.run(main())
