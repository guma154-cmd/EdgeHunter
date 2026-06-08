import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

from database import AsyncDatabase, OddsTimeSeries


API_URL = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/"
BOOKMAKERS_OF_INTEREST = {"pinnacle", "bet365", "marathonbet", "williamhill"}
SLEEP_SECONDS = 7200

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edgehunter.steam_crawler")


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key() -> str:
    for key in ("THE_ODDS_API_KEY", "ODDS_API_KEY", "EDGEHUNTER_API_KEY"):
        value = os.getenv(key)
        if value:
            return value
    raise RuntimeError("THE_ODDS_API_KEY nao encontrada no .env.")


def parse_commence_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def extract_h2h_odds(
    event: dict[str, Any],
    bookmaker: dict[str, Any],
) -> OddsTimeSeries | None:
    home_team = event.get("home_team")
    away_team = event.get("away_team")
    if not home_team or not away_team:
        return None

    for market in bookmaker.get("markets", []):
        if market.get("key") != "h2h":
            continue

        outcomes = {
            outcome.get("name"): outcome.get("price")
            for outcome in market.get("outcomes", [])
        }
        home_odd = outcomes.get(home_team)
        draw_odd = outcomes.get("Draw")
        away_odd = outcomes.get(away_team)

        if home_odd is None or draw_odd is None or away_odd is None:
            return None

        return OddsTimeSeries(
            event_id=str(event["id"]),
            sport_key=str(event["sport_key"]),
            home_team=str(home_team),
            away_team=str(away_team),
            commence_time=parse_commence_time(str(event["commence_time"])),
            capture_timestamp=datetime.utcnow(),
            bookmaker=str(bookmaker["key"]),
            home_odd=float(home_odd),
            draw_odd=float(draw_odd),
            away_odd=float(away_odd),
        )

    return None


async def fetch_odds(api_key: str) -> tuple[list[dict[str, Any]], str | None]:
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params, timeout=30) as response:
            remaining = response.headers.get("x-requests-remaining")
            if response.status != 200:
                body = await response.text()
                raise RuntimeError(f"The Odds API erro {response.status}: {body[:300]}")
            data = await response.json()
            if not isinstance(data, list):
                raise RuntimeError("The Odds API retornou payload inesperado.")
            return data, remaining


async def persist_rows(rows: list[OddsTimeSeries]) -> None:
    if not rows:
        return

    db = AsyncDatabase()
    async with db.AsyncSessionLocal() as session:
        session.add_all(rows)
        await session.commit()


async def run_cycle() -> None:
    api_key = get_api_key()
    events, remaining = await fetch_odds(api_key)

    rows: list[OddsTimeSeries] = []
    for event in events:
        for bookmaker in event.get("bookmakers", []):
            if bookmaker.get("key") not in BOOKMAKERS_OF_INTEREST:
                continue
            row = extract_h2h_odds(event, bookmaker)
            if row is not None:
                rows.append(row)

    await persist_rows(rows)
    logger.info(
        "Steam crawler: inseridas=%s eventos=%s requests_remaining=%s",
        len(rows),
        len(events),
        remaining,
    )


async def main() -> None:
    load_env_file()
    while True:
        try:
            await run_cycle()
        except Exception:
            logger.exception("Steam crawler: ciclo falhou")
        await asyncio.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
