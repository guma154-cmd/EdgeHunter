"""
EdgeHunter — OddsPortal/OddsAgora Scraper (Playwright)
Coleta odds de Pinnacle, Betfair, Bet365 e Betano sem limites de API.
Adaptado para o mercado brasileiro (OddsAgora).
"""
import asyncio
import logging
import random
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

TARGET_BOOKMAKERS = {
    'pinnacle': ['pinnacle'],
    'betfair': ['betfair'],
    'bet365': ['bet365'],
    'betano': ['betano']
}

LEAGUES_URLS = {
    'Premier League': 'https://www.oddsagora.com.br/football/england/campeonato-ingles/',
    'La Liga': 'https://www.oddsagora.com.br/football/spain/laliga/',
    'Bundesliga': 'https://www.oddsagora.com.br/football/germany/bundesliga/',
    'Serie A': 'https://www.oddsagora.com.br/football/italy/serie-a/',
    'Ligue 1': 'https://www.oddsagora.com.br/football/france/ligue-1/',
    'Brasileirao': 'https://www.oddsagora.com.br/football/brazil/brasileirao-betano/',
    'Champions League': 'https://www.oddsagora.com.br/football/europe/liga-dos-campeoes/',
    'Libertadores': 'https://www.oddsagora.com.br/football/south-america/copa-libertadores/',
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

class OddsPortalScraper:
    def __init__(self):
        self.browser = None
        self.context = None

    async def _init_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080}
        )

    async def fetch_games_with_odds(self) -> list:
        all_games = []
        async with async_playwright() as p:
            await self._init_browser(p)
            try:
                for league_name, url in LEAGUES_URLS.items():
                    logger.info(f"Scraping league: {league_name}")
                    page = await self.context.new_page()
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(5000)
                        
                        links = await page.eval_on_selector_all('a', 'elements => elements.map(e => e.href)')
                        
                        # Regex mais flexível para links de partidas
                        # Procura por qualquer link que tenha o slug da liga e termine com um ID (alfanumérico de 5-10 chars)
                        match_links = []
                        base_path = url.replace('https://www.oddsagora.com.br', '')
                        for l in links:
                            if base_path in l and len(l.split('/')) >= 6:
                                slug = l.split('/')[-2]
                                if '-' in slug and len(slug.split('-')[-1]) >= 5:
                                    if l not in match_links and l != url:
                                        match_links.append(l)
                        
                        logger.info(f"Encontrados {len(match_links)} links de partidas em {league_name}")
                        
                        count = 0
                        for match_url in match_links:
                            if count >= 3: break
                            
                            game_data = await self._scrape_match_odds(page, match_url, league_name)
                            if game_data and len(game_data.get('all_odds', {})) >= 2:
                                all_games.append(game_data)
                                count += 1
                                logger.info(f"Coletado: {game_data['home_team']} vs {game_data['away_team']}")
                            
                            await page.wait_for_timeout(2000)
                            
                    except Exception as e:
                        logger.error(f"Erro em {league_name}: {e}")
                    finally:
                        await page.close()
            finally:
                await self.browser.close()
        
        return all_games

    async def _scrape_match_odds(self, page, url, league_name) -> dict:
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            title_tag = soup.find('h1')
            if not title_tag: return None
            title_text = title_tag.get_text()
            if ' - ' not in title_text: return None
            
            teams = title_text.split(' - ', 1)
            home_team = teams[0].strip()
            away_team = teams[1].strip()
            
            all_odds = {}
            # Buscar bookmakers e suas odds
            # Geralmente as odds estão em divs com classes como 'odds-val' ou em spans
            rows = soup.find_all(['div', 'tr'], recursive=True)
            
            for row in rows:
                row_text = row.get_text().lower()
                bookie_name = None
                
                for target, variations in TARGET_BOOKMAKERS.items():
                    if any(v in row_text for v in variations):
                        bookie_name = target
                        break
                
                if bookie_name and bookie_name not in all_odds:
                    odds = []
                    # Procurar por números que pareçam odds
                    for item in row.find_all(['p', 'span', 'div']):
                        val_str = item.get_text().strip().replace(',', '.')
                        try:
                            val = float(val_str)
                            if 1.01 < val < 50.0:
                                odds.append(val)
                        except: continue
                    
                    if len(odds) >= 3:
                        all_odds[bookie_name] = {'home': odds[0], 'draw': odds[1], 'away': odds[2]}
            
            if not all_odds: return None
            return {
                'home_team': home_team, 'away_team': away_team,
                'league': league_name, 'match_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'all_odds': all_odds, 'source': 'oddsportal'
            }
        except Exception as e: return None

def fetch_games_sync() -> list:
    try: return asyncio.run(OddsPortalScraper().fetch_games_with_odds())
    except Exception as e: return []
