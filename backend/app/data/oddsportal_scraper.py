"""
EdgeHunter — OddsPortal/OddsAgora Scraper Otimizado (Playwright)
"""
import asyncio
import logging
import random
import time
import os
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests
try:
    from playwright_stealth import Stealth
    async def apply_stealth(page): await Stealth().apply_stealth_async(page)
except:
    async def apply_stealth(page): pass

logger = logging.getLogger(__name__)

DEFAULT_LEAGUES = {
    'Brasileirao': 'https://www.oddsagora.com.br/football/brazil/brasileirao-betano/',
    'Premier League': 'https://www.oddsagora.com.br/football/england/campeonato-ingles/',
    'ATP Madrid': 'https://www.oddsagora.com.br/tenis/espanha/atp-madri/',
    'Tenis Geral': 'https://www.oddsagora.com.br/tenis/',
}

TARGET_BOOKMAKERS = {'pinnacle': ['pinnacle'], 'betfair': ['betfair'], 'bet365': ['bet365'], 'betano': ['betano']}
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"]

class OddsPortalScraper:
    async def fetch_games_with_odds(self) -> list:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            all_games = []
            for name, url in DEFAULT_LEAGUES.items():
                page = await ctx.new_page(); await apply_stealth(page)
                try:
                    print(f"Scraping {name}...")
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(5000)
                    content = await page.content(); soup = BeautifulSoup(content, 'lxml')
                    links = []
                    for a in soup.find_all('a', href=True):
                        if "/h2h/" in a['href'] or "/vencedor/" in a['href']:
                            links.append((urljoin('https://www.oddsagora.com.br', a['href']), a.get_text()))
                    
                    for m_url, m_text in links[:10]:
                        sport = 'tennis' if 'tenis' in url or 'tennis' in url else 'football'
                        await page.goto(m_url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(2000)
                        m_content = await page.content(); m_soup = BeautifulSoup(m_content, 'lxml')
                        teams = m_text.split(' vs ') if ' vs ' in m_text else ["Home", "Away"]
                        all_odds = {}
                        for row in m_soup.find_all(['div', 'tr']):
                            row_t = row.get_text().lower(); b_name = next((t for t, v in TARGET_BOOKMAKERS.items() if any(x in row_t for x in v)), None)
                            if b_name and b_name not in all_odds:
                                odds = [float(el.get_text().replace(',', '.')) for el in row.find_all(['p', 'span']) if el.get_text().replace(',', '.').replace('.', '').isdigit()]
                                if sport == 'tennis' and len(odds) >= 2: all_odds[b_name] = {'home': odds[0], 'away': odds[1]}
                                elif len(odds) >= 3: all_odds[b_name] = {'home': odds[0], 'draw': odds[1], 'away': odds[2]}
                        if all_odds: all_games.append({'home_team': teams[0], 'away_team': teams[-1], 'league': name, 'all_odds': all_odds, 'sport': sport, 'source': 'oddsportal'})
                except: pass
                finally: await page.close()
            await browser.close()
            return all_games

def fetch_games_sync() -> list:
    try: return asyncio.run(OddsPortalScraper().fetch_games_with_odds())
    except: return []
