import asyncio
import json
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

class Bet365Scraper:
    """
    Intercepta chamadas de API interna do Bet365
    durante navegação via Playwright.
    """
    
    TARGET_URL = "https://www.bet365.com/"
    FOOTBALL_URL = "https://www.bet365.com/#/AC/B1/C1/D8/"
    
    def __init__(self):
        self.odds_data = []
        self.stealth_config = Stealth()
    
    async def fetch_odds(self) -> list:
        games = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox','--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            await self.stealth_config.apply_stealth_async(page)
            
            # Interceptar respostas JSON da Bet365
            async def handle_response(response):
                if 'bet365' in response.url and response.status == 200:
                    ct = response.headers.get('content-type','')
                    if 'json' in ct:
                        try:
                            data = await response.json()
                            self._parse_odds(data, games)
                        except:
                            pass
            
            page.on('response', handle_response)
            
            try:
                logger.info(f"[Bet365] Navegando para {self.FOOTBALL_URL}")
                await page.goto(
                    self.FOOTBALL_URL,
                    wait_until='networkidle',
                    timeout=60000
                )
                await page.wait_for_timeout(10000) # Esperar carregar mais dados
            except Exception as e:
                logger.error(f"[Bet365] Erro durante a navegação: {e}")
            finally:
                await browser.close()
        
        logger.info(f"[Bet365] {len(games)} jogos coletados")
        # Remover duplicatas básicas
        unique_games = []
        seen = set()
        for g in games:
            key = f"{g['home_team']}_{g['away_team']}"
            if key not in seen:
                unique_games.append(g)
                seen.add(key)
        
        return unique_games
    
    def _parse_odds(self, data: dict, games: list):
        """Parsear estrutura JSON da Bet365."""
        try:
            if isinstance(data, dict):
                # Bet365 costuma retornar dados em formatos variados ou aninhados
                events = (
                    data.get('events', []) or
                    data.get('fixtures', []) or
                    data.get('data', {}).get('events', []) or
                    data.get('results', [])
                )
                
                # Se for uma lista direta de eventos
                if isinstance(events, list):
                    for event in events:
                        home = event.get('homeTeam','') or event.get('home','') or event.get('participant1','')
                        away = event.get('awayTeam','') or event.get('away','') or event.get('participant2','')
                        
                        if not home or not away:
                            continue
                            
                        markets = event.get('markets', []) or event.get('odds', [])
                        home_odd = away_odd = draw_odd = None
                        
                        for market in markets:
                            m_name = str(market.get('name', '')).lower()
                            if '1x2' in m_name or 'resultado' in m_name or 'match' in m_name:
                                outcomes = market.get('outcomes', market.get('selections', []))
                                for o in outcomes:
                                    name = str(o.get('name','')).lower()
                                    price = o.get('price') or o.get('odds') or o.get('decimal')
                                    if price:
                                        price = float(price)
                                        if 'home' in name or str(home).lower() in name or name == '1':
                                            home_odd = price
                                        elif 'away' in name or str(away).lower() in name or name == '2':
                                            away_odd = price
                                        elif 'draw' in name or 'empate' in name or name == 'x':
                                            draw_odd = price
                                            
                        if home_odd and away_odd:
                            odds_map = {'home': home_odd, 'away': away_odd}
                            if draw_odd:
                                odds_map['draw'] = draw_odd
                            
                            games.append({
                                'home_team':  str(home),
                                'away_team':  str(away),
                                'league':     event.get('league','') or event.get('competition',''),
                                'sport':      'football',
                                'match_date': event.get('date','') or event.get('startTime',''),
                                'source':     'bet365',
                                'all_odds':   {'bet365': odds_map}
                            })
        except Exception as e:
            # logger.debug(f"[Bet365] Parse erro: {e}")
            pass

def fetch_bet365_sync() -> list:
    scraper = Bet365Scraper()
    try:
        return asyncio.run(scraper.fetch_odds())
    except Exception as e:
        print(f"Erro ao rodar scraper Bet365: {e}")
        return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Iniciando teste do scraper Bet365...")
    res = fetch_bet365_sync()
    print(f"Resultado final: {len(res)} jogos.")
    if res:
        print(f"Primeiro jogo: {res[0]['home_team']} vs {res[0]['away_team']}")
