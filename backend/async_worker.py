import asyncio
import inspect
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from redis import asyncio as aioredis
from sqlalchemy.exc import SQLAlchemyError

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.detection.value_detector import ValueDetector
from database import AsyncDatabase, OddsHistory, ValueOpportunityLog
from utils.telegram_bot import AsyncTelegramBot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ODDS_QUEUE_KEY = os.getenv("ODDS_QUEUE_KEY", "raw_odds_queue")
BLPOP_TIMEOUT_SECONDS = int(os.getenv("WORKER_BLPOP_TIMEOUT_SECONDS", "1"))
BOOKMAKER_NAME = os.getenv("WORKER_BOOKMAKER_NAME", "BetsAPI_Mock")
MARKET_TYPE = os.getenv("WORKER_MARKET_TYPE", "1X2")
MIN_EDGE_PCT = float(os.getenv("WORKER_MIN_EDGE_PCT", "0.0"))

class AsyncOddsWorker:
    def __init__(self) -> None:
        self.redis_client: aioredis.Redis | None = None
        self.database = AsyncDatabase()
        self.detector = ValueDetector(min_edge_pct=MIN_EDGE_PCT)
        self.telegram_bot = AsyncTelegramBot()
        self.telegram_polling_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self.redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await self.redis_client.ping()
        await self.database.init_db()
        logger.info("Async worker conectado ao Redis e PostgreSQL.")

    async def close(self) -> None:
        if self.telegram_polling_task is not None:
            self.telegram_polling_task.cancel()
            try:
                await self.telegram_polling_task
            except asyncio.CancelledError:
                pass
        if self.redis_client is not None:
            await self.redis_client.close()
        await self.telegram_bot.close()
        await self.database.engine.dispose()
        logger.info("Async worker finalizado.")

    async def run_forever(self) -> None:
        await self.connect()
        self.telegram_polling_task = asyncio.create_task(
            self.telegram_bot.start_polling(self.redis_client, self.database.AsyncSessionLocal)
        )
        try:
            while True:
                try:
                    message = await self.redis_client.blpop(
                        ODDS_QUEUE_KEY,
                        timeout=BLPOP_TIMEOUT_SECONDS,
                    )
                    if message is None:
                        continue

                    _, payload = message
                    await self.process_message(payload)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception("Erro no loop do worker; continuando consumo: %s", exc)
                    await asyncio.sleep(1)
        finally:
            await self.close()

    async def process_message(self, payload: str) -> None:
        try:
            raw_event = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.warning("Mensagem descartada: JSON inválido: %s", exc)
            return

        pinnacle_raw = raw_event.get("pinnacle_odds")
        if not pinnacle_raw:
            logger.warning("Evento %s descartado: Sem dados da Pinnacle.", event_id(raw_event))
            return

        try:
            pinnacle_odds = validate_odds(pinnacle_raw)
            # A fair probability baseline SEMPRE derivada do shape (Pinnacle)
            fair_probs = build_fair_probability_baseline(pinnacle_odds)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Mensagem descartada: odds Pinnacle inválidas: %s", exc)
            return

        home_team = str(raw_event.get("home_team") or raw_event.get("home") or "Home")
        away_team = str(raw_event.get("away_team") or raw_event.get("away") or "Away")

        # 1. Persistência do baseline (Pinnacle) no histórico de CLV
        pinnacle_name = str(pinnacle_raw.get("bookmaker", "Pinnacle"))
        await self.persist_odds_history(raw_event, pinnacle_odds, pinnacle_name)

        soft_odds_list = raw_event.get("soft_odds", [])
        for soft_raw in soft_odds_list:
            try:
                soft_odds = validate_odds(soft_raw)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Odds Soft ignoradas devido a dados inválidos: %s", exc)
                continue
            
            soft_name = str(soft_raw.get("bookmaker", BOOKMAKER_NAME))
            
            # 2. Persistência da Soft sendo percorrida no loop
            await self.persist_odds_history(raw_event, soft_odds, soft_name)

            # 3. Cálculo de Edge individual
            analyze_result = self.detector.analyze(
                home_team=home_team,
                away_team=away_team,
                our_probs=fair_probs,
                pinnacle_odds=pinnacle_odds,
                soft_odds={soft_name: soft_odds},
            )
            opportunities = await analyze_result if inspect.isawaitable(analyze_result) else analyze_result

            if not opportunities:
                logger.info("Evento %s (%s) consumido sem oportunidade validada.", event_id(raw_event), soft_name)
                continue

            for opportunity in opportunities:
                await self.persist_opportunity(raw_event, opportunity)

    async def persist_odds_history(
        self,
        raw_event: dict[str, Any],
        odds: dict[str, float],
        bookmaker: str,
    ) -> None:
        history = OddsHistory(
            event_id=event_id(raw_event),
            league=raw_event.get("league"),
            home_team=raw_event.get("home_team"),
            away_team=raw_event.get("away_team"),
            bookmaker=bookmaker,
            market_type=MARKET_TYPE,
            event_start_time=parse_event_timestamp(raw_event),
            home_odd=float(odds["home"]),
            draw_odd=float(odds["draw"]),
            away_odd=float(odds["away"]),
            raw_odds_source=raw_event,
        )

        try:
            async with self.database.AsyncSessionLocal() as session:
                session.add(history)
                await session.commit()
            logger.info(
                "Histórico de odds persistido: event_id=%s bookmaker=%s home=%.4f draw=%.4f away=%.4f",
                history.event_id,
                history.bookmaker,
                history.home_odd,
                history.draw_odd,
                history.away_odd,
            )
        except SQLAlchemyError as exc:
            logger.exception("Erro de banco ao persistir histórico de odds; worker continua: %s", exc)
        except Exception as exc:
            logger.exception("Erro inesperado ao persistir histórico de odds; worker continua: %s", exc)

    async def persist_opportunity(self, raw_event: dict[str, Any], opportunity: dict[str, Any]) -> None:
        log = ValueOpportunityLog(
            timestamp=parse_event_timestamp(raw_event),
            event_id=event_id(raw_event),
            bookmaker=str(opportunity.get("bookmaker") or BOOKMAKER_NAME),
            market_type=str(opportunity.get("market") or MARKET_TYPE),
            selection=str(opportunity["selection"]),
            odd=float(opportunity["odd"]),
            true_probability=float(opportunity["our_prob"]),
            value_edge=float(opportunity["edge_pct"]) / 100.0,
            stake=float(opportunity.get("kelly_stake") or 0.0),
            bankroll_snapshot=float(getattr(self.detector, 'current_bankroll_balance', 1000.0)),
            match_details={
                "home_team": opportunity.get("home_team") or raw_event.get("home_team"),
                "away_team": opportunity.get("away_team") or raw_event.get("away_team"),
                "league": raw_event.get("league"),
                "market": opportunity.get("market"),
                "confidence": opportunity.get("confidence"),
                "has_edge_vs_pinnacle": opportunity.get("has_edge_vs_pinnacle"),
            },
            raw_odds_source=raw_event,
        )

        try:
            async with self.database.AsyncSessionLocal() as session:
                session.add(log)
                await session.commit()
            cache_key = f"alerted:{log.event_id}:{log.selection}"
            already_alerted = await self.redis_client.exists(cache_key)
            if already_alerted:
                logger.info(
                    "Oportunidade já alertada nas ultimas 12h: event_id=%s selection=%s",
                    log.event_id,
                    log.selection,
                )
            else:
                await self.telegram_bot.send_opportunity_alert(log, log.match_details)
                await self.redis_client.setex(cache_key, 43200, "1")
            logger.info(
                "Oportunidade persistida: event_id=%s selection=%s edge=%.4f stake=%.2f",
                log.event_id,
                log.selection,
                log.value_edge,
                log.stake,
            )
        except SQLAlchemyError as exc:
            logger.exception("Erro de banco ao persistir oportunidade; worker continua: %s", exc)
        except Exception as exc:
            logger.exception("Erro inesperado ao persistir oportunidade; worker continua: %s", exc)


def validate_odds(odds_dict: Dict[str, Any]) -> Dict[str, float]:
    """Valida e retorna os dados brutos como float maior que 1.0."""
    odds = {
        "home": float(odds_dict["home"]),
        "draw": float(odds_dict["draw"]),
        "away": float(odds_dict["away"])
    }
    for selection, odd in odds.items():
        if odd <= 1.0:
            raise ValueError(f"{selection} odd must be > 1.0")
    return odds


def build_fair_probability_baseline(odds: dict[str, float]) -> dict[str, float]:
    implied = {selection: 1.0 / odd for selection, odd in odds.items()}
    overround = sum(implied.values())
    if overround <= 0:
        raise ValueError("overround must be positive")
    return {selection: probability / overround for selection, probability in implied.items()}


def event_id(raw_event: dict[str, Any]) -> str:
    return str(raw_event.get("match_id") or raw_event.get("event_id") or raw_event.get("id") or "unknown")


def parse_event_timestamp(raw_event: dict[str, Any]) -> datetime:
    value = raw_event.get("timestamp")
    if not value:
        return datetime.now(timezone.utc)

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def main() -> None:
    worker = AsyncOddsWorker()
    await worker.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrompido pelo usuário.")
