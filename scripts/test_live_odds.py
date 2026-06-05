import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

UPCOMING_URL = "https://api.betsapi.com/v2/events/upcoming"
ODDS_URL = "https://api.betsapi.com/v2/event/odds"

LEAGUES_OF_INTEREST = {
    "FIFA World Cup 2026": 15,
    "Brazil Serie A": 325,
    "Brazil Serie B": 326,
    "USA MLS": 132,
    "Argentina Liga Profesional": 155,
    "Japan J1 League": 292,
    "Norway Eliteserien": 374,
    "Sweden Allsvenskan": 393,
}


def event_time_utc(event: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(event.get("time", 0)), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict[str, str]) -> dict[str, Any]:
    async with session.get(url, params=params, timeout=30) as response:
        response.raise_for_status()
        return await response.json(content_type=None)


async def find_first_event_in_next_24h(session: aiohttp.ClientSession, token: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    limit = now + timedelta(hours=24)

    for league_name, league_id in LEAGUES_OF_INTEREST.items():
        payload = await fetch_json(
            session,
            UPCOMING_URL,
            {
                "token": token,
                "sport_id": "1",
                "league_id": str(league_id),
            },
        )

        results = payload.get("results") or []
        logger.info("Liga=%s league_id=%s eventos_retornados=%s", league_name, league_id, len(results))

        for event in results:
            starts_at = event_time_utc(event)
            if starts_at is None:
                continue
            if now <= starts_at <= limit:
                logger.info(
                    "Evento alvo encontrado: league=%s event_id=%s starts_at=%s home=%s away=%s",
                    league_name,
                    event.get("id"),
                    starts_at.isoformat(),
                    (event.get("home") or {}).get("name"),
                    (event.get("away") or {}).get("name"),
                )
                return event

    return None


async def main() -> None:
    token = os.getenv("BETSAPI_KEY", "")
    if not token:
        raise RuntimeError("BETSAPI_KEY ausente no ambiente.")

    async with aiohttp.ClientSession() as session:
        event = await find_first_event_in_next_24h(session, token)
        if event is None:
            logger.warning("Nenhum evento encontrado nas proximas 24h para as ligas auditadas.")
            print(json.dumps({"success": 0, "error": "no_event_in_next_24h"}, ensure_ascii=False, indent=2))
            return

        event_id = str(event["id"])
        odds_payload = await fetch_json(
            session,
            ODDS_URL,
            {
                "token": token,
                "event_id": event_id,
            },
        )

        print(json.dumps(odds_payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
