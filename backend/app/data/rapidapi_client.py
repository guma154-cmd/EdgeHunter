"""
EdgeHunter — RapidAPI (API-Football) Client
Busca odds pré-jogo das partidas via RapidAPI (fallback gratuito).
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

# Mapeamento de ligas (API-Football -> EdgeHunter normalizado)
LEAGUES_MAP = {
    39: 'Premier League',
    140: 'La Liga',
    78: 'Bundesliga',
    135: 'Serie A',
    61: 'Ligue 1',
    71: 'Brasileirão'
}

class RapidAPIClient:
    """
    Cliente para API-Football via RapidAPI.
    Plano free: 100 req/dia.
    """
    
    BASE_URL = 'https://api-football-v1.p.rapidapi.com/v3'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=params or {},
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"RapidAPI Erro {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Erro RapidAPIClient: {e}")
        return None

    def get_upcoming_fixtures(self) -> List[Dict]:
        """Busca os próximos 2 dias das ligas rastreadas."""
        today = datetime.now(pytz.utc).date()
        tomorrow = today + timedelta(days=1)
        
        all_fixtures = []
        for league_id in LEAGUES_MAP.keys():
            # Buscar jogos de hoje
            res = self._get('/fixtures', {'league': league_id, 'season': today.year, 'date': today.strftime('%Y-%m-%d')})
            if res and 'response' in res:
                all_fixtures.extend(res['response'])
                
            # Buscar jogos de amanhã
            res = self._get('/fixtures', {'league': league_id, 'season': today.year, 'date': tomorrow.strftime('%Y-%m-%d')})
            if res and 'response' in res:
                all_fixtures.extend(res['response'])
                
        return all_fixtures

    def fetch_odds(self) -> List[Dict]:
        """
        Busca odds para as fixtures e formata como OddsAPIClient.
        """
        fixtures = self.get_upcoming_fixtures()
        if not fixtures:
            return []
            
        opportunities = []
        for fix in fixtures:
            fixture_id = fix['fixture']['id']
            league_id = fix['league']['id']
            league_name = LEAGUES_MAP.get(league_id, 'Desconhecida')
            
            home_team = fix['teams']['home']['name']
            away_team = fix['teams']['away']['name']
            match_date = fix['fixture']['date']
            
            # Buscar odds
            odds_data = self._get('/odds', {'fixture': fixture_id, 'bookmaker': 8}) # 8 = bet365 para referência? Pinnacle is usually 17 or we search in bookmakers
            # Vamos tentar puxar sem filtro de bookmaker para ver todas
            odds_res = self._get('/odds', {'fixture': fixture_id})
            
            if not odds_res or not odds_res.get('response'):
                continue
                
            bookmakers = odds_res['response'][0]['bookmakers']
            
            pinnacle_odds = None
            soft_odds = {}
            
            for bookie in bookmakers:
                name = bookie['name'].lower()
                
                # Pegar o mercado Match Winner (id 1)
                match_winner = next((m for m in bookie['bets'] if m['name'] == 'Match Winner'), None)
                if not match_winner:
                    continue
                    
                # Values: Home, Draw, Away
                h_odd, d_odd, a_odd = 0, 0, 0
                for val in match_winner['values']:
                    if val['value'] == 'Home': h_odd = float(val['odd'])
                    elif val['value'] == 'Draw': d_odd = float(val['odd'])
                    elif val['value'] == 'Away': a_odd = float(val['odd'])
                
                if not (h_odd and d_odd and a_odd):
                    continue
                
                b_odds = {'home': h_odd, 'draw': d_odd, 'away': a_odd}
                
                if 'pinnacle' in name:
                    pinnacle_odds = b_odds
                elif any(soft in name for soft in ['bet365', '1xbet', 'bwin', 'betano']):
                    soft_odds[name] = b_odds

            # Se Pinnacle não disponível, usa a melhor soft odd como aproximação
            if not pinnacle_odds and soft_odds:
                pinnacle_odds = list(soft_odds.values())[0]

            if pinnacle_odds and soft_odds:
                opportunities.append({
                    'external_id': str(fixture_id),
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league_name,
                    'match_date': match_date,
                    'pinnacle': pinnacle_odds,
                    'soft_books': soft_odds
                })
                
        return opportunities
