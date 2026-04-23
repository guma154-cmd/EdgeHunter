"""
EdgeHunter — Football-Data.org Client
Busca histórico gratuito de resultados para treinamento dos modelos.
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Leagues disponíveis no tier gratuito
LEAGUES_FREE = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1',
    'CL': 'Champions League',
    'PPL': 'Primeira Liga',
    'DED': 'Eredivisie',
    'BSA': 'Brasileirão'
}


class FootballDataClient:
    """
    Cliente para Football-Data.org API.
    Tier gratuito: 10 req/min, dados históricos completos.
    """
    
    BASE_URL = 'https://api.football-data.org/v4'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Auth-Token': api_key})
    
    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Request com rate limiting automático."""
        import time
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=params or {},
                timeout=20
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limit. Aguardando 60s...")
                time.sleep(60)
                return self._get(endpoint, params)
            else:
                logger.error(f"FD API Error {response.status_code}: {response.text[:300]}")
        
        except Exception as e:
            logger.error(f"Erro Football-Data: {e}")
        
        return None
    
    def get_matches(
        self,
        competition_code: str,
        season: int = None,
        status: str = 'FINISHED'
    ) -> List[Dict]:
        """
        Busca partidas de uma competição.
        
        Args:
            competition_code: ex: 'PL', 'PD', 'BL1'
            season: Ano da temporada (ex: 2023 = 2023/24)
            status: 'FINISHED', 'SCHEDULED', 'LIVE'
        """
        params = {'status': status}
        if season:
            params['season'] = season
        
        data = self._get(f'/competitions/{competition_code}/matches', params)
        
        if not data:
            return []
        
        return data.get('matches', [])
    
    def get_historical_matches_df(
        self,
        competition_codes: List[str] = None,
        seasons: List[int] = None
    ) -> pd.DataFrame:
        """
        Coleta histórico de resultados e retorna como DataFrame.
        Pronto para treinamento dos modelos.
        """
        if competition_codes is None:
            competition_codes = list(LEAGUES_FREE.keys())[:6]  # Top 6 por padrão
        
        if seasons is None:
            current_year = datetime.now().year
            seasons = list(range(current_year - 3, current_year))
        
        all_matches = []
        
        for code in competition_codes:
            league_name = LEAGUES_FREE.get(code, code)
            
            for season in seasons:
                logger.info(f"Buscando: {league_name} {season}/{season+1}")
                matches = self.get_matches(code, season, 'FINISHED')
                
                for match in matches:
                    normalized = self._normalize_match(match, league_name)
                    if normalized:
                        all_matches.append(normalized)
                
                import time
                time.sleep(7)  # Respeitar rate limit: 10 req/min
        
        df = pd.DataFrame(all_matches)
        
        if not df.empty:
            df['match_date'] = pd.to_datetime(df['match_date']).dt.tz_localize(None)
            df = df.sort_values('match_date').reset_index(drop=True)
            logger.info(f"Total: {len(df)} partidas históricas carregadas")
        
        return df
    
    def _normalize_match(self, match: Dict, league: str) -> Optional[Dict]:
        """Normaliza uma partida da API."""
        try:
            score = match.get('score', {})
            full_time = score.get('fullTime', {})
            
            home_score = full_time.get('home')
            away_score = full_time.get('away')
            
            if home_score is None or away_score is None:
                return None
            
            return {
                'external_id': str(match['id']),
                'league': league,
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'home_team_id': str(match['homeTeam']['id']),
                'away_team_id': str(match['awayTeam']['id']),
                'home_score': int(home_score),
                'away_score': int(away_score),
                'match_date': match['utcDate'],
                'season': match.get('season', {}).get('startDate', '')[:4],
                'matchday': match.get('matchday'),
                'stage': match.get('stage', 'REGULAR_SEASON'),
                'status': match.get('status', 'FINISHED')
            }
        except Exception as e:
            logger.debug(f"Erro ao normalizar partida: {e}")
            return None
    
    def get_standings(self, competition_code: str, season: int = None) -> Optional[Dict]:
        """Tabela de classificação (features de forma)."""
        params = {}
        if season:
            params['season'] = season
        return self._get(f'/competitions/{competition_code}/standings', params)
    
    def get_recent_results(self, days: int = 3) -> List[Dict]:
        """Resultados recentes para liquidação das apostas."""
        all_recent = []
        
        for code in list(LEAGUES_FREE.keys())[:8]:
            data = self._get(
                f'/competitions/{code}/matches',
                {'status': 'FINISHED', 'limit': 10}
            )
            if data:
                for match in data.get('matches', []):
                    normalized = self._normalize_match(match, LEAGUES_FREE.get(code, code))
                    if normalized:
                        all_recent.append(normalized)
        
        return all_recent
