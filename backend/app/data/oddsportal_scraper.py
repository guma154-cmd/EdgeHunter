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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
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
                        
                        # Cookies
                        try:
                            btn = page.get_by_role("button", name="Aceito")
                            if await btn.is_visible(): await btn.click()
                        except: pass
                        
                        await page.wait_for_timeout(5000)
                        
                        # Pegar links e textos
                        links_data = await page.eval_on_selector_all('a', '''elements => elements.map(e => ({
                            href: e.href,
                            text: e.innerText
                        }))''')
                        
                        match_links = []
                        for l in links_data:
                            href = l['href']
                            text = l['text']
                            # Padrão: links H2H que contêm '#' e têm times no texto
                            if "/h2h/" in href and "#" in href and "vs" in text.lower():
                                if href not in [m[0] for m in match_links]:
                                    match_links.append((href, text))
                        
                        logger.info(f"Encontrados {len(match_links)} links de partidas em {league_name}")
                        
                        count = 0
                        for match_url, match_text in match_links:
                            if count >= 3: break
                            game_data = await self._scrape_match_odds(page, match_url, league_name, match_text)
                            if game_data and len(game_data.get('all_odds', {})) >= 1:
                                all_games.append(game_data)
                                count += 1
                                logger.info(f"Coletado: {game_data['home_team']} vs {game_data['away_team']} ({len(game_data['all_odds'])} casas)")
                            await page.wait_for_timeout(2000)
                            
                    except Exception as e:
                        logger.error(f"Erro em {league_name}: {e}")
                    finally:
                        await page.close()
            finally:
                await self.browser.close()
        
        return all_games

    async def _scrape_match_odds(self, page, url, league_name, match_text) -> dict:
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Times do texto (ex: Sunderland vs Nottingham - 24/04/2026)
            clean_text = match_text.split('-')[0].strip()
            if " vs " in clean_text.lower():
                home_team, away_team = [t.strip() for t in clean_text.split(" vs ")]
            else:
                home_team, away_team = "Home", "Away"

            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            all_odds = {}
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
                    for el in row.find_all(['p', 'span']):
                        t = el.get_text().strip().replace(',', '.')
                        try:
                            v = float(t)
                            if 1.01 < v < 50.0: odds.append(v)
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
