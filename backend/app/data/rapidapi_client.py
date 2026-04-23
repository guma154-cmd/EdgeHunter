"""
EdgeHunter — RapidAPI (API-Football) Client
Busca odds de múltiplas casas para Surebet com Rate Limiter.
"""
import requests
import logging
import json
import os
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

USAGE_FILE = 'rapidapi_usage.json'

class RapidAPIClient:
    """
    Cliente para API-Football via RapidAPI.
    Plano free: 100 req/dia.
    Implementa Rate Limiter e Coleta Multi-Bookmaker para Surebet.
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
        self._load_usage()

    def _load_usage(self):
        """Carrega contador de requisições do dia."""
        today = datetime.now().strftime('%Y-%m-%d')
        if os.path.exists(USAGE_FILE):
            try:
                with open(USAGE_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == today:
                        self.daily_requests = data.get('count', 0)
                    else:
                        self.daily_requests = 0
            except:
                self.daily_requests = 0
        else:
            self.daily_requests = 0

    def _save_usage(self):
        """Salva contador de requisições."""
        today = datetime.now().strftime('%Y-%m-%d')
        with open(USAGE_FILE, 'w') as f:
            json.dump({'date': today, 'count': self.daily_requests}, f)

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        # Rate Limiter Check
        if self.daily_requests >= 95:
            logger.warning("🚨 RapidAPI: Limite de 95 requisições atingido. Pausando.")
            return None
        
        if self.daily_requests == 80:
            from app.alerts.telegram_bot import send_message
            send_message("⚠️ *Aviso RapidAPI*: 80 requisições utilizadas hoje.")

        try:
            response = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=params or {},
                timeout=15
            )
            self.daily_requests += 1
            self._save_usage()

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"RapidAPI Erro {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Erro RapidAPIClient: {e}")
        return None

    def get_today_fixtures(self) -> List[Dict]:
        """Busca fixtures de hoje em uma única chamada de liga ou geral."""
        today = datetime.now(pytz.utc).strftime('%Y-%m-%d')
        
        # Para economizar, buscamos todos os jogos do dia (1 req por liga)
        all_fixtures = []
        for league_id in LEAGUES_MAP.keys():
            res = self._get('/fixtures', {'league': league_id, 'season': 2026, 'date': today})
            if res and 'response' in res:
                all_fixtures.extend(res['response'])
        return all_fixtures

    def fetch_odds(self) -> List[Dict]:
        """
        Busca odds para as fixtures e formata para Surebet.
        Prioriza jogos nas próximas 3 horas.
        """
        all_fixtures = self.get_today_fixtures()
        if not all_fixtures:
            return []
            
        now = datetime.now(pytz.utc)
        three_hours_later = now + timedelta(hours=3)
        
        # Filtrar e Priorizar
        relevant_fixtures = []
        for fix in all_fixtures:
            match_time = datetime.fromisoformat(fix['fixture']['date'].replace('Z', '+00:00'))
            if now <= match_time <= three_hours_later:
                relevant_fixtures.append(fix)
        
        # Limitar a no máximo 10 jogos por ciclo para economizar quota
        relevant_fixtures = relevant_fixtures[:10]
        
        opportunities = []
        for fix in relevant_fixtures:
            fixture_id = fix['fixture']['id']
            league_id = fix['league']['id']
            league_name = LEAGUES_MAP.get(league_id, 'Desconhecida')
            
            home_team = fix['teams']['home']['name']
            away_team = fix['teams']['away']['name']
            match_date = fix['fixture']['date']
            
            # Buscar odds de todas as casas (1 req por jogo)
            odds_res = self._get('/odds', {'fixture': fixture_id})
            
            if not odds_res or not odds_res.get('response'):
                continue
                
            bookmakers_data = odds_res['response'][0]['bookmakers']
            all_odds = {}
            
            for bookie in bookmakers_data:
                name = bookie['name'].lower()
                # Filtrar apenas casas do nosso escopo
                if not any(target in name for target in ['bet365', 'betano', 'superbet', 'pinnacle']):
                    continue
                
                match_winner = next((m for m in bookie['bets'] if m['name'] == 'Match Winner'), None)
                if not match_winner:
                    continue
                    
                h_odd, d_odd, a_odd = 0, 0, 0
                for val in match_winner['values']:
                    if val['value'] == 'Home': h_odd = float(val['odd'])
                    elif val['value'] == 'Draw': d_odd = float(val['odd'])
                    elif val['value'] == 'Away': a_odd = float(val['odd'])
                
                if h_odd and a_odd:
                    all_odds[name] = {'home': h_odd, 'draw': d_odd, 'away': a_odd}

            if len(all_odds) >= 2:  # Precisa de pelo menos 2 casas para arbitragem
                opportunities.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league_name,
                    'match_date': match_date,
                    'all_odds': all_odds
                })
                
        return opportunities
