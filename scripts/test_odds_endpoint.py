import asyncio
import json
import logging
import os

import aiohttp


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BETSAPI_ODDS_URL = "https://api.betsapi.com/v2/event/odds"
EVENT_ID = "11143533"


async def main() -> None:
    token = os.getenv("BETSAPI_KEY", "")
    if not token:
        raise RuntimeError("BETSAPI_KEY ausente no ambiente.")

    params = {
        "token": token,
        "event_id": EVENT_ID,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BETSAPI_ODDS_URL, params=params, timeout=30) as response:
            body = await response.json(content_type=None)

    logger.info("BETSAPI_ODDS_RAW event_id=%s payload=%s", EVENT_ID, json.dumps(body, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
