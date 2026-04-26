"""
EdgeHunter — Ingestion de Dados: The Odds API
Busca odds em tempo real da Pinnacle e casas soft.
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


# Mapeamento de sports keys da API → nomes amigáveis
SPORTS_MAP = {
    'soccer_epl': 'Premier League',
    'soccer_spain_la_liga': 'La Liga',
    'soccer_germany_bundesliga': 'Bundesliga',
    'soccer_italy_serie_a': 'Serie A',
    'soccer_france_ligue_one': 'Ligue 1',
    'soccer_uefa_champs_league': 'Champions League',
    'soccer_brazil_campeonato': 'Brasileirão',
    'soccer_portugal_primeira_liga': 'Primeira Liga',
    'soccer_netherlands_eredivisie': 'Eredivisie',
    'tennis_atp_madrid': 'ATP Madrid',
    'tennis_wta_madrid': 'WTA Madrid',
    'tennis_atp_savannah_challenger': 'ATP Savannah',
    'tennis_wta_oeiras': 'WTA Oeiras',
}


class OddsAPIClient:
    """
    Cliente para The Odds API.
    Documentação: https://the-odds-api.com/liveapi/guides/v4/
    """
    
    BASE_URL = 'https://api.the-odds-api.com/v4'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.requests_remaining = None
        self.requests_used = None
    
    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Faz request GET com tratamento de erros."""
        params = params or {}
        params['apiKey'] = self.api_key
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
                timeout=15
            )
            
            # Rastrear uso de quota
            self.requests_remaining = response.headers.get('x-requests-remaining')
            self.requests_used = response.headers.get('x-requests-used')
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("API key inválida ou expirada")
            elif response.status_code == 429:
                logger.warning(f"Rate limit atingido. Remaining: {self.requests_remaining}")
            else:
                logger.error(f"Erro API: {response.status_code} - {response.text[:200]}")
        
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição à Odds API")
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão com Odds API")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
        
        return None
    
    def get_sports(self) -> List[Dict]:
        """Lista todas as ligas disponíveis."""
        return self._get('/sports') or []
    
    def get_odds(
        self,
        sport_key: str,
        regions: str = 'eu',
        markets: str = 'h2h',
        bookmakers: str = None
    ) -> Optional[List[Dict]]:
        """
        Busca odds para uma liga específica.
        
        Args:
            sport_key: ex: 'soccer_epl'
            regions: 'eu', 'uk', 'us', 'au'
            markets: 'h2h' (1X2), 'totals' (over/under), 'spreads'
            bookmakers: Lista separada por vírgula, ex: 'pinnacle,bet365'
        """
        params = {
            'regions': regions,
            'markets': markets,
            'oddsFormat': 'decimal',
            'dateFormat': 'iso'
        }
        
        if bookmakers:
            params['bookmakers'] = bookmakers
        
        data = self._get(f'/sports/{sport_key}/odds', params)
        return data
    
    def get_scores(self, sport_key: str, days_from: int = 1) -> Optional[List[Dict]]:
        """Busca placares recentes e ao vivo."""
        return self._get(
            f'/sports/{sport_key}/scores',
            {'daysFrom': days_from, 'dateFormat': 'iso'}
        )
    
    def fetch_all_value_games(
        self,
        bookmakers_filter: List[str] = None
    ) -> List[Dict]:
        """
        Busca odds de todas as ligas monitoradas.
        Retorna jogos normalizados com odds da Pinnacle e casas soft.
        """
        all_games = []
        
        for sport_key, league_name in SPORTS_MAP.items():
            logger.info(f"Buscando odds: {league_name}")
            
            data = self.get_odds(
                sport_key=sport_key,
                regions='eu',
                markets='h2h'
            )
            
            if not data:
                continue
            
            for event in data:
                normalized = self._normalize_event(event, league_name)
                if normalized:
                    all_games.append(normalized)
        
        logger.info(f"Total de jogos coletados: {len(all_games)}")
        return all_games
    
    def _normalize_event(self, event: Dict, league: str) -> Optional[Dict]:
        """
        Normaliza um evento da API para o formato interno do EdgeHunter.
        """
        try:
            game = {
                'external_id': event['id'],
                'league': league,
                'home_team': event['home_team'],
                'away_team': event['away_team'],
                'match_date': event['commence_time'],
                'pinnacle_home': None,
                'pinnacle_draw': None,
                'pinnacle_away': None,
                'soft_odds': {}
            }
            
            # Processar bookmakers
            for bookmaker in event.get('bookmakers', []):
                book_key = bookmaker['key']
                
                for market in bookmaker.get('markets', []):
                    if market['key'] != 'h2h':
                        continue
                    
                    outcomes = {o['name']: o['price'] for o in market['outcomes']}
                    
                    home_odd = outcomes.get(event['home_team'])
                    away_odd = outcomes.get(event['away_team'])
                    draw_odd = outcomes.get('Draw')
                    
                    if not home_odd or not away_odd:
                        continue
                    
                    if book_key == 'pinnacle':
                        game['pinnacle_home'] = home_odd
                        game['pinnacle_away'] = away_odd
                        game['pinnacle_draw'] = draw_odd
                    else:
                        game['soft_odds'][book_key] = {
                            'home': home_odd,
                            'draw': draw_odd,
                            'away': away_odd
                        }
            
            return game
        
        except Exception as e:
            logger.debug(f"Erro ao normalizar evento: {e}")
            return None
    
    def get_quota_status(self) -> Dict:
        """Retorna status da cota de requisições."""
        return {
            'remaining': self.requests_remaining,
            'used': self.requests_used
        }
