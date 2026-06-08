import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.proxy_rotator import ProxyRotator

logger = logging.getLogger(__name__)

NormalizedOdd = Dict[str, Any]

PINNACLE_ID = os.getenv("PINNACLE_ID", "PinnacleSports").strip(' "\'')
soft_env = os.getenv("SOFT_BOOKIES_IDS", "Bet365,BWin,1XBet").strip(' "\'')
SOFT_BOOKIES_IDS = [x.strip() for x in soft_env.split(",")]

class BetsAPIClient:
    """
    Cliente para a BetsAPI com fluxo em duas etapas:
    1. v2/events/upcoming para calendário.
    2. v2/event/odds para odds 1X2 por event_id.
    Faz a Dupla Ingestão (Sharp + Soft).
    """

    UPCOMING_URL = "https://api.betsapi.com/v2/events/upcoming"
    ODDS_URL = "https://api.betsapi.com/v2/event/odds"
    ODDS_THROTTLE_SECONDS = 0.2

    def __init__(
        self,
        api_key: str,
        proxy_rotator: ProxyRotator,
        leagues_of_interest: Dict[str, int],
    ):
        self.api_key = api_key
        self.proxy_rotator = proxy_rotator
        self.leagues_of_interest = leagues_of_interest
        if not api_key:
            logger.warning("API Key da BetsAPI não foi fornecida. O cliente operará em modo mock.")

    async def get_upcoming_fixtures(self, hours_ahead: int = 4) -> List[NormalizedOdd]:
        """
        Busca eventos dentro da janela e enriquece com odds.
        """
        if not self.api_key:
            return self._get_mock_data()

        all_fixtures: List[NormalizedOdd] = []
        session = await self.proxy_rotator.get_client_session()

        for league_name, league_id in self.leagues_of_interest.items():
            proxy_url, proxy_auth = await self._get_proxy_details()
            params = {
                "token": self.api_key,
                "sport_id": "1",
                "league_id": str(league_id),
            }

            try:
                logger.info("Buscando calendario da liga '%s' (ID: %s) na BetsAPI.", league_name, league_id)
                async with session.get(
                    self.UPCOMING_URL,
                    params=params,
                    proxy=proxy_url,
                    proxy_auth=proxy_auth,
                    timeout=20,
                ) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)

                if data.get("success") != 1 or "results" not in data:
                    logger.error("Erro na resposta de '%s': %s", league_name, data.get("error", "Sem detalhes"))
                    continue

                events = self._filter_events_by_window(data["results"], hours_ahead)
                logger.info(
                    "Encontrados %s eventos dentro da janela para liga '%s'. Buscando odds 1X2.",
                    len(events),
                    league_name
                )

                league_fixtures_count = 0
                for event in events:
                    await asyncio.sleep(self.ODDS_THROTTLE_SECONDS)
                    normalized = await self._build_fixture_with_odds(session, event)
                    if normalized is not None:
                        all_fixtures.append(normalized)
                        league_fixtures_count += 1

                logger.info("Liga '%s': %s fixtures com odds 1X2 prontos para Redis.", league_name, league_fixtures_count)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error("Erro de rede ao buscar liga '%s': %s", league_name, e)
                if proxy_url:
                    await self.proxy_rotator.mark_proxy_bad(proxy_url)
            except Exception as e:
                logger.error("Erro inesperado ao processar liga '%s': %s", league_name, e, exc_info=True)

        return all_fixtures

    async def _fetch_odds_for_source(self, session: aiohttp.ClientSession, event_id: str, proxy_url: str, proxy_auth: Any, source_id: str) -> Any:
        params = {
            "token": self.api_key,
            "event_id": event_id.strip(),
            "source": source_id.strip()
        }
        async with session.get(
            self.ODDS_URL,
            params=params,
            proxy=proxy_url,
            proxy_auth=proxy_auth,
            timeout=20,
        ) as response:
            response.raise_for_status()
            return await response.json(content_type=None)

    async def _build_fixture_with_odds(
        self,
        session: aiohttp.ClientSession,
        event: Dict[str, Any],
    ) -> Optional[NormalizedOdd]:
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            logger.warning("Evento descartado sem event_id: %s", event)
            return None

        proxy_url, proxy_auth = await self._get_proxy_details()

        try:
            try:
                pinnacle_payload = await self._fetch_odds_for_source(session, event_id, proxy_url, proxy_auth, PINNACLE_ID)
            except Exception as e:
                logger.warning("Erro real na Pinnacle para evento %s: %s", event_id, e)
                return None
            
            await asyncio.sleep(1.5)

            if pinnacle_payload.get("success") != 1 or not pinnacle_payload.get("results"):
                logger.warning("Evento %s descartado: Pinnacle indisponível (Payload: %s)", event_id, pinnacle_payload.get("error", pinnacle_payload))
                return None

            try:
                pin_odds_data = pinnacle_payload["results"]["odds"]["1_1"][0]
                pinnacle_odds = {
                    "bookmaker": "Pinnacle",
                    "bookmaker_id": PINNACLE_ID,
                    "home": float(pin_odds_data["home_od"]),
                    "draw": float(pin_odds_data["draw_od"]),
                    "away": float(pin_odds_data["away_od"])
                }
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.warning("Evento %s descartado: Pinnacle indisponível (dados invalidos) %s", event_id, e)
                return None

            soft_odds_list = []
            for soft_id in SOFT_BOOKIES_IDS:
                try:
                    soft_payload = await self._fetch_odds_for_source(session, event_id, proxy_url, proxy_auth, soft_id)
                except Exception as e:
                    logger.warning("Erro real na casa Soft %s para evento %s: %s", soft_id, event_id, e)
                    continue
                
                await asyncio.sleep(1.5)

                if soft_payload.get("success") != 1 or not soft_payload.get("results"):
                    continue
                try:
                    soft_data = soft_payload["results"]["odds"]["1_1"][0]
                    # Tenta mapear o nome amigável ou fallback para o ID
                    bookie_name = "Bet365" if soft_id in ("1", "bet365") else "Betano" if soft_id in ("32", "betano") else f"Soft_{soft_id}"
                    
                    soft_odds_list.append({
                        "bookmaker": bookie_name,
                        "bookmaker_id": soft_id,
                        "home": float(soft_data["home_od"]),
                        "draw": float(soft_data["draw_od"]),
                        "away": float(soft_data["away_od"])
                    })
                except (KeyError, IndexError, TypeError, ValueError):
                    continue

            if not soft_odds_list:
                logger.info("Evento %s descartado: odds invalidas nas casas Soft", event_id)
                return None

            event_time_utc = datetime.fromtimestamp(int(event["time"]), tz=timezone.utc)

            return {
                "event_id": event_id,
                "timestamp": event_time_utc.isoformat(),
                "league": event.get("league", {}).get("name"),
                "home_team": event.get("home", {}).get("name"),
                "away_team": event.get("away", {}).get("name"),
                "pinnacle_odds": pinnacle_odds,
                "soft_odds": soft_odds_list,
                "raw_source": "BetsAPI_Dual",
                "raw_data": {
                    "event": event
                },
            }

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error("Erro de rede ao buscar odds do evento %s: %s", event_id, e)
            if proxy_url:
                await self.proxy_rotator.mark_proxy_bad(proxy_url)
            return None
        except Exception as e:
            logger.error("Erro inesperado ao buscar odds do evento %s: %s", event_id, e, exc_info=True)
            return None

    def _filter_events_by_window(
        self,
        results: List[Dict[str, Any]],
        hours_ahead: int,
    ) -> List[Dict[str, Any]]:
        now_utc = datetime.now(timezone.utc)
        time_limit_utc = now_utc + timedelta(hours=hours_ahead)
        filtered: List[Dict[str, Any]] = []

        for event in results:
            try:
                event_time_utc = datetime.fromtimestamp(int(event.get("time", 0)), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                logger.warning("Evento descartado por timestamp invalido: %s", event.get("id"))
                continue

            if now_utc < event_time_utc < time_limit_utc:
                filtered.append(event)

        return filtered

    async def _get_proxy_details(self) -> Tuple[Optional[str], Optional[aiohttp.BasicAuth]]:
        proxy_details = await self.proxy_rotator.get_next_proxy_details()
        return proxy_details if proxy_details else (None, None)

    def _get_mock_data(self) -> List[NormalizedOdd]:
        logger.info("Retornando dados mockados pois a API key da BetsAPI não foi configurada.")
        now = datetime.now(timezone.utc)
        return [
            {
                "event_id": "mock_12345",
                "timestamp": (now + timedelta(hours=1)).isoformat(),
                "league": "Mock League",
                "home_team": "Mock Team A",
                "away_team": "Mock Team B",
                "pinnacle_odds": {
                    "bookmaker": "Pinnacle",
                    "bookmaker_id": "73",
                    "home": 2.10,
                    "draw": 3.40,
                    "away": 3.80
                },
                "soft_odds": [
                    {
                        "bookmaker": "Bet365",
                        "bookmaker_id": "1",
                        "home": 2.15,
                        "draw": 3.30,
                        "away": 3.50
                    }
                ],
                "raw_source": "BetsAPI_Mock_Dual",
                "raw_data": {},
            }
        ]
