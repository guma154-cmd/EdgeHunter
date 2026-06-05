import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.proxy_rotator import ProxyRotator

logger = logging.getLogger(__name__)

NormalizedOdd = Dict[str, Any]


class BetsAPIClient:
    """
    Cliente para a BetsAPI com fluxo em duas etapas:
    1. v2/events/upcoming para calendário.
    2. v2/event/odds para odds 1X2 por event_id.
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
        Busca eventos dentro da janela e enriquece cada evento com odds 1X2
        obtidas em v2/event/odds.
        """
        if not self.api_key:
            return self._get_mock_data()

        all_fixtures: List[NormalizedOdd] = []

        for league_name, league_id in self.leagues_of_interest.items():
            session = await self.proxy_rotator.get_client_session()
            proxy_url, proxy_auth = await self._get_proxy_details()
            params = {
                "token": self.api_key,
                "league_id": str(league_id),
                "sport_id": "1",
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
                    logger.error(
                        "Erro na resposta de calendario da BetsAPI para liga '%s': %s",
                        league_name,
                        data.get("error", "Sem detalhes"),
                    )
                    continue

                events = self._filter_events_by_window(data["results"], hours_ahead)
                logger.info(
                    "Encontrados %s eventos dentro da janela para liga '%s'. Buscando odds 1X2.",
                    len(events),
                    league_name,
                )

                for event in events:
                    await asyncio.sleep(self.ODDS_THROTTLE_SECONDS)
                    normalized = await self._build_fixture_with_odds(session, event)
                    if normalized is not None:
                        all_fixtures.append(normalized)

                logger.info(
                    "Liga '%s': %s fixtures com odds 1X2 prontos para Redis.",
                    league_name,
                    len([fixture for fixture in all_fixtures if fixture.get("league") == league_name]),
                )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error("Erro de rede ao buscar calendario da BetsAPI para liga '%s': %s", league_name, e)
                if proxy_url:
                    await self.proxy_rotator.mark_proxy_bad(proxy_url)
            except Exception as e:
                logger.error(
                    "Erro inesperado ao processar calendario da BetsAPI para liga '%s': %s",
                    league_name,
                    e,
                    exc_info=True,
                )

        return all_fixtures

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
        params = {
            "token": self.api_key,
            "event_id": event_id,
        }

        try:
            async with session.get(
                self.ODDS_URL,
                params=params,
                proxy=proxy_url,
                proxy_auth=proxy_auth,
                timeout=20,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)

            odds_data = payload["results"]["odds"]["1_1"][0]
            home_odd = float(odds_data["home_od"])
            draw_odd = float(odds_data["draw_od"])
            away_odd = float(odds_data["away_od"])
            event_time_utc = datetime.fromtimestamp(int(event["time"]), tz=timezone.utc)

            return {
                "match_id": event_id,
                "timestamp": event_time_utc.isoformat(),
                "league": event.get("league", {}).get("name"),
                "home_team": event.get("home", {}).get("name"),
                "away_team": event.get("away", {}).get("name"),
                "home_odd": home_odd,
                "draw_odd": draw_odd,
                "away_odd": away_odd,
                "raw_source": "BetsAPI",
                "raw_data": {
                    "event": event,
                    "odds": odds_data,
                },
            }

        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.info("Evento %s descartado: odds 1X2 indisponiveis ou invalidas: %s", event_id, e)
            return None
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
                "match_id": "mock_12345",
                "timestamp": (now + timedelta(hours=1)).isoformat(),
                "league": "Mock League",
                "home_team": "Mock Team A",
                "away_team": "Mock Team B",
                "home_odd": 2.10,
                "draw_odd": 3.40,
                "away_odd": 3.80,
                "raw_source": "BetsAPI_Mock",
                "raw_data": {},
            }
        ]
