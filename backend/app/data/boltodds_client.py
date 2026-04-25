import asyncio
import json
import logging

import websockets

logger = logging.getLogger(__name__)

TARGET_BOOKS = ['bet365', 'betano', 'pinnacle', 'betfair']

LEAGUES_SOCCER = [
    'Brazil Serie A',
    'EPL',
    'Champions League',
    'La Liga',
    'Bundesliga',
    'Serie A',
    'Ligue 1',
]


class BoltOddsClient:
    WS_URL = "wss://spro.agency/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.games = {}
        self.connected = False

    async def connect_and_collect(self, duration_seconds: int = 30) -> list:
        """
        Conecta ao WebSocket, coleta odds por duration_seconds
        e retorna lista de game_data com all_odds.
        """
        uri = f"{self.WS_URL}?key={self.api_key}"
        try:
            async with websockets.connect(uri, ping_timeout=10) as ws:
                await ws.recv()
                self.connected = True
                logger.info("[BoltOdds] Conectado")

                sub = {
                    "action": "subscribe",
                    "filters": {
                        "sports": ["Soccer"],
                        "sportsbooks": TARGET_BOOKS,
                        "markets": ["Moneyline"],
                    },
                }
                await ws.send(json.dumps(sub))

                deadline = asyncio.get_event_loop().time() + duration_seconds
                while asyncio.get_event_loop().time() < deadline:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        self._process_message(json.loads(msg))
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"[BoltOdds] Erro recv: {e}")
                        break

        except Exception as e:
            logger.error(f"[BoltOdds] Erro conexão: {e}")
            self.connected = False

        return self._build_game_list()

    def _process_message(self, data: dict):
        """Processa mensagem do WebSocket e agrupa por jogo."""
        try:
            game_key = f"{data.get('home')}_{data.get('away')}_{data.get('date', '')}"
            book = data.get('sportsbook', '').lower()
            market = data.get('market', '')
            league = data.get('league', '')

            if 'moneyline' not in market.lower():
                return
            if not any(t in book for t in TARGET_BOOKS):
                return
            if league and league not in LEAGUES_SOCCER:
                return

            if game_key not in self.games:
                self.games[game_key] = {
                    'home_team': data.get('home', ''),
                    'away_team': data.get('away', ''),
                    'league': league,
                    'match_date': data.get('date', ''),
                    'source': 'boltodds',
                    'all_odds': {},
                }

            outcomes = data.get('outcomes', [])
            odds_map = {}
            for o in outcomes:
                name = o.get('name', '').lower()
                price = o.get('price', 0)
                if 'home' in name or data.get('home', '').lower() in name:
                    odds_map['home'] = float(price)
                elif 'away' in name or data.get('away', '').lower() in name:
                    odds_map['away'] = float(price)
                elif 'draw' in name or 'tie' in name:
                    odds_map['draw'] = float(price)

            if len(odds_map) >= 2:
                book_key = next((t for t in TARGET_BOOKS if t in book), book)
                self.games[game_key]['all_odds'][book_key] = odds_map

        except Exception as e:
            logger.error(f"[BoltOdds] Erro process: {e}")

    def _build_game_list(self) -> list:
        """Retorna só jogos com 2+ casas."""
        return [
            g for g in self.games.values()
            if len(g.get('all_odds', {})) >= 2
        ]


def fetch_games_boltodds(api_key: str, duration: int = 30) -> list:
    """Wrapper síncrono para o scheduler."""
    client = BoltOddsClient(api_key)
    return asyncio.run(client.connect_and_collect(duration))
