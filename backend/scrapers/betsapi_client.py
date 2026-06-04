import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from backend.proxy_rotator import ProxyRotator

logger = logging.getLogger(__name__)

# Contrato de dados normalizado para o EdgeHunter
NormalizedOdd = Dict[str, Any]

class BetsAPIClient:
    """
    Cliente para a BetsAPI com lógica de Janela de Alvo e parser resiliente.
    """
    BASE_URL = "https://api.b365api.com/v2/events/upcoming"

    def __init__(
        self,
        api_key: str,
        proxy_rotator: ProxyRotator,
        leagues_of_interest: Dict[str, int]
    ):
        """
        Args:
            api_key: Chave da API da BetsAPI.
            proxy_rotator: Instância do ProxyRotator para gerenciar sessões e proxies.
            leagues_of_interest: Dicionário de {nome_liga: id_da_liga}.
        """
        self.api_key = api_key
        self.proxy_rotator = proxy_rotator
        self.leagues_of_interest = leagues_of_interest
        if not api_key:
            logger.warning("API Key da BetsAPI não foi fornecida. O cliente operará em modo mock.")

    async def get_upcoming_fixtures(self, hours_ahead: int = 4) -> List[NormalizedOdd]:
        """
        Busca os próximos jogos (fixtures) das ligas de interesse que começam
        nas próximas `hours_ahead` horas.
        """
        if not self.api_key:
            return self._get_mock_data()

        all_fixtures = []
        # A BetsAPI não suporta múltiplas ligas em um só request de forma eficiente.
        # Teremos que fazer um request por liga.
        for league_name, league_id in self.leagues_of_interest.items():
            params = {
                "token": self.api_key,
                "league_id": str(league_id),
                "sport_id": "1", # Futebol
            }
            
            session = await self.proxy_rotator.get_client_session()
            proxy_url, proxy_auth = await self.proxy_rotator.get_next_proxy_details()

            try:
                logger.info(f"Buscando jogos da liga '{league_name}' (ID: {league_id}) na BetsAPI.")
                async with session.get(self.BASE_URL, params=params, proxy=proxy_url, proxy_auth=proxy_auth, timeout=20) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if data.get('success') == 1 and 'results' in data:
                        fixtures = self._parse_and_filter(data['results'], hours_ahead)
                        all_fixtures.extend(fixtures)
                        logger.info(f"Encontrados {len(fixtures)} jogos relevantes da liga '{league_name}'.")
                    else:
                        logger.error(f"Erro na resposta da BetsAPI para a liga '{league_name}': {data.get('error', 'Sem detalhes')}")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Erro de rede ao buscar dados da BetsAPI para a liga '{league_name}': {e}")
                if proxy_url:
                    await self.proxy_rotator.mark_proxy_bad(proxy_url)
            except Exception as e:
                logger.error(f"Erro inesperado ao processar dados da BetsAPI para a liga '{league_name}': {e}", exc_info=True)
        
        return all_fixtures

    def _parse_and_filter(self, results: List[Dict[str, Any]], hours_ahead: int) -> List[NormalizedOdd]:
        """
        Faz o parsing dos resultados da API e filtra pela janela de tempo.
        """
        parsed_fixtures = []
        now_utc = datetime.now(timezone.utc)
        time_limit_utc = now_utc + timedelta(hours=hours_ahead)

        for event in results:
            try:
                event_time_utc = datetime.fromtimestamp(int(event.get('time', 0)), tz=timezone.utc)
                
                # 1. Filtra por janela de tempo
                if not (now_utc < event_time_utc < time_limit_utc):
                    continue

                # 2. Normaliza os dados para o contrato do EdgeHunter
                # A BetsAPI retorna as odds de 1X2 no campo 'main' -> 'sp' -> 'full_time_result'
                odds_data = event.get('main', {}).get('sp', {}).get('full_time_result', {}).get('odds', [])
                
                if len(odds_data) < 3:
                    continue # Pula se não houver odds de 1X2

                # O 'header' pode não estar presente, assumimos a ordem Home, Draw, Away
                home_odd = float(odds_data[0]['odds'])
                draw_odd = float(odds_data[1]['odds'])
                away_odd = float(odds_data[2]['odds'])

                normalized = {
                    "match_id": event.get('id'),
                    "timestamp": event_time_utc.isoformat(),
                    "league": event.get('league', {}).get('name'),
                    "home_team": event.get('home', {}).get('name'),
                    "away_team": event.get('away', {}).get('name'),
                    "home_odd": home_odd,
                    "draw_odd": draw_odd,
                    "away_odd": away_odd,
                    "raw_source": "BetsAPI",
                    "raw_data": event # Guarda o evento original para depuração
                }
                parsed_fixtures.append(normalized)

            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.warning(f"Erro de parsing no evento ID {event.get('id')}: {e}. Pulando.")
                continue
                
        return parsed_fixtures

    def _get_mock_data(self) -> List[NormalizedOdd]:
        """Retorna dados mockados para testes quando a API key não está presente."""
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
                "raw_data": {}
            }
        ]
