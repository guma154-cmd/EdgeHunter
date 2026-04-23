"""
EdgeHunter — Odds-API.io Client
100 requisições por hora gratuitas.
"""
import requests
import logging
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

USAGE_FILE = 'oddsapiio_usage.json'

class OddsApiIoClient:
    """
    Cliente para Odds-API.io (v3).
    Plano free: 100 req/hora.
    """
    
    BASE_URL = 'https://api.odds-api.io/v3'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self._load_usage()

    def _load_usage(self):
        """Carrega contador de requisições da hora atual."""
        now = datetime.now()
        hour_key = now.strftime('%Y-%m-%d %H')
        if os.path.exists(USAGE_FILE):
            try:
                with open(USAGE_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get('hour') == hour_key:
                        self.hourly_requests = data.get('count', 0)
                    else:
                        self.hourly_requests = 0
            except:
                self.hourly_requests = 0
        else:
            self.hourly_requests = 0

    def _save_usage(self):
        """Salva contador de requisições."""
        hour_key = datetime.now().strftime('%Y-%m-%d %H')
        with open(USAGE_FILE, 'w') as f:
            json.dump({'hour': hour_key, 'count': self.hourly_requests}, f)

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        self._load_usage()
        if self.hourly_requests >= 98:
            logger.warning("🚨 Odds-API.io: Limite de 100 requisições/hora atingido.")
            return None

        request_params = params or {}
        request_params['apiKey'] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=request_params,
                timeout=15
            )
            self.hourly_requests += 1
            self._save_usage()

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Odds-API.io Erro {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Erro OddsApiIoClient: {e}")
        return None

    def fetch_games_with_odds(self) -> List[Dict]:
        """
        Busca odds de futebol.
        """
        # 1. Buscar eventos LIVE primeiro (mais chance de ter odds reais agora)
        events_res = self._get('/events', {'sport': 'football', 'status': 'live', 'limit': 10})
        if not events_res or not isinstance(events_res, list):
            # Fallback para pendentes
            events_res = self._get('/events', {'sport': 'football', 'status': 'pending', 'limit': 10})
            
        if not events_res or not isinstance(events_res, list):
            return []
            
        formatted_games = []
        for event in events_res:
            event_id = event['id']
            home_team = event['home']
            away_team = event['away']
            match_date = event['date']
            league_name = event.get('league', {}).get('name', 'Soccer')
            
            # 2. Buscar odds para este evento específico
            # Tentamos Bet365 e Betano
            odds_res = self._get('/odds', {
                'eventId': event_id, 
                'bookmakers': 'Bet365,Betano'
            })
            
            if not odds_res or 'bookmakers' not in odds_res:
                continue
                
            all_odds = {}
            bookmakers_data = odds_res['bookmakers']
            
            for bookie_name, markets in bookmakers_data.items():
                name_key = bookie_name.lower()
                
                # MoneyLine
                ml_market = next((m for m in markets if m['name'] == 'ML'), None)
                if not ml_market: continue
                
                odds_list = ml_market.get('odds', [])
                if not odds_list: continue
                
                odds_val = odds_list[0]
                # Alguns retornos podem vir como string ou float
                try:
                    h_odd = float(odds_val.get('home', 0))
                    d_odd = float(odds_val.get('draw', 0))
                    a_odd = float(odds_val.get('away', 0))
                except:
                    continue
                
                if h_odd and a_odd:
                    all_odds[name_key] = {'home': h_odd, 'draw': d_odd, 'away': a_odd}
            
            # Restaurar para >= 2 para Surebet real
            if len(all_odds) >= 2:
                formatted_games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league_name,
                    'match_date': match_date,
                    'all_odds': all_odds
                })
                
        return formatted_games

    def fetch_odds(self) -> List[Dict]:
        return self.fetch_games_with_odds()
