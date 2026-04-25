"""
EdgeHunter — OddsPortal/OddsAgora Scraper Otimizado (Playwright)
Meta: < 60 segundos por ciclo.
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
    from playwright_stealth import stealth_async
except ImportError:
    from playwright_stealth.stealth import stealth_async
from app.alerts.telegram_bot import send_message

logger = logging.getLogger(__name__)

# OTIMIZAÇÃO 2 — Configuração de ligas via ENV ou Top 3
DEFAULT_LEAGUES = {
    'Brasileirao':      'https://www.oddsagora.com.br/football/brazil/brasileirao-betano/',
    'Premier League':   'https://www.oddsagora.com.br/football/england/campeonato-ingles/',
    'Champions League': 'https://www.oddsagora.com.br/football/europe/liga-dos-campeoes/',
}

def _get_active_leagues():
    leagues_env = os.getenv('SCRAPER_LEAGUES', '').lower()
    if not leagues_env:
        return DEFAULT_LEAGUES
    
    active = {}
    if 'brasileirao' in leagues_env: active['Brasileirao'] = DEFAULT_LEAGUES['Brasileirao']
    if 'premier' in leagues_env:     active['Premier League'] = DEFAULT_LEAGUES['Premier League']
    if 'champions' in leagues_env:   active['Champions League'] = DEFAULT_LEAGUES['Champions League']
    return active or DEFAULT_LEAGUES

LEAGUES_URLS = _get_active_leagues()

TARGET_BOOKMAKERS = {
    'pinnacle': ['pinnacle'],
    'betfair': ['betfair'],
    'bet365': ['bet365'],
    'betano': ['betano']
}

# CORREÇÃO 4 — Rotação de User-Agent real (10 agentes)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# CORREÇÃO 4 — Headers realistas
REALISTIC_HEADERS = {
    'User-Agent': USER_AGENTS[0],
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com.br/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}

# OTIMIZAÇÃO 3 — Cache de jogos do dia
_games_cache = {
    'date': None,
    'match_urls': {}  # {league_name: [(url, text), ...]}
}


def _absolute_url(href: str) -> str:
    return urljoin('https://www.oddsagora.com.br', href)


def _fetch_html_via_requests(url: str, timeout: int = 30) -> str | None:
    try:
        response = requests.get(
            _absolute_url(url),
            headers={**REALISTIC_HEADERS, 'User-Agent': random.choice(USER_AGENTS)},
            timeout=timeout
        )
        if response.status_code == 200:
            return response.text
        logger.warning(f"HTTP fallback retornou {response.status_code} para {url}")
    except Exception as exc:
        logger.warning(f"HTTP fallback falhou para {url}: {exc}")
    return None


def _extract_match_links_from_html(html: str) -> list:
    soup = BeautifulSoup(html, 'lxml')
    found_links = []

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        text = anchor.get_text(' ', strip=True)
        if "/h2h/" in href and "#" in href and "vs" in text.lower():
            absolute_href = _absolute_url(href)
            if absolute_href not in [link[0] for link in found_links]:
                found_links.append((absolute_href, text))

    return found_links

def _get_cached_match_links(league_name: str) -> list:
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if _games_cache['date'] == today and league_name in _games_cache['match_urls']:
        return _games_cache['match_urls'][league_name]
    return []

def _update_cache(league_name: str, links: list):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if _games_cache['date'] != today:
        _games_cache['date'] = today
        _games_cache['match_urls'] = {}
    _games_cache['match_urls'][league_name] = links

class OddsPortalScraper:
    def __init__(self):
        self.browser = None
        self.context = None

    async def _init_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        # CORREÇÃO 4 — Rotação de User-Agent
        self.context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1280, 'height': 720},
            extra_http_headers=REALISTIC_HEADERS
        )

    # OTIMIZAÇÃO 1 — Scraping paralelo de ligas
    async def fetch_games_with_odds(self) -> list:
        async with async_playwright() as p:
            await self._init_browser(p)
            
            tasks = [
                self._scrape_league(league_name, url)
                for league_name, url in LEAGUES_URLS.items()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_games = []
            for result in results:
                if isinstance(result, list):
                    all_games.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Erro em task de liga: {result}")
            
            if self.browser:
                await self.browser.close()
            return all_games

    async def _scrape_league(self, league_name, url) -> list:
        league_games = []
        page = await self.context.new_page()
        # CORREÇÃO 1 — Playwright Stealth
        await stealth_async(page)
        
        try:
            # CORREÇÃO 4 — Sleep randômico
            await asyncio.sleep(random.uniform(1.5, 3.5))
            
            # OTIMIZAÇÃO 3 — Verificar cache
            match_links = _get_cached_match_links(league_name)
            
            if not match_links:
                found_links = []
                try:
                    await page.goto(_absolute_url(url), wait_until="domcontentloaded", timeout=15000)
                    
                    try:
                        btn = page.get_by_role("button", name="Aceito")
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                    except Exception:
                        pass
                    
                    await page.wait_for_timeout(1000)
                    
                    links_data = await page.eval_on_selector_all('a', '''elements => elements.map(e => ({
                        href: e.href,
                        text: e.innerText
                    }))''')
                    
                    for link_data in links_data:
                        href = link_data['href']
                        text = link_data['text']
                        if "/h2h/" in href and "#" in href and "vs" in text.lower():
                            absolute_href = _absolute_url(href)
                            if absolute_href not in [match[0] for match in found_links]:
                                found_links.append((absolute_href, text))
                except Exception as exc:
                    logger.warning(f"Fallback HTTP ativado para {league_name}: {exc}")
                    html = _fetch_html_via_requests(url, timeout=30)
                    if html:
                        found_links = _extract_match_links_from_html(html)
                
                match_links = found_links[:5] # Limite de 5 jogos por liga para velocidade
                _update_cache(league_name, match_links)
                logger.info(f"Descobertos {len(match_links)} links para {league_name}")
            
            # Coletar odds de cada partida (agora sempre usando os links do cache se disponíveis)
            for match_url, match_text in match_links:
                game_data = await self._scrape_match_odds(page, match_url, league_name, match_text)
                if game_data and len(game_data.get('all_odds', {})) >= 1:
                    league_games.append(game_data)
                    
        except Exception as e:
            logger.error(f"Erro processando liga {league_name}: {e}")
        finally:
            await page.close()
        
        return league_games

    async def _scrape_match_odds(self, page, url, league_name, match_text) -> dict:
        try:
            # CORREÇÃO 4 — Sleep randômico
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            clean_text = match_text.split('-')[0].strip()
            if " vs " in clean_text.lower():
                home_team, away_team = [t.strip() for t in clean_text.split(" vs ")]
            else:
                home_team, away_team = "Home", "Away"

            content = None
            try:
                await page.goto(_absolute_url(url), wait_until="domcontentloaded", timeout=12000)
                await page.wait_for_timeout(1000)
                content = await page.content()
            except Exception as exc:
                logger.warning(f"Fallback HTTP ativado para partida {url}: {exc}")
                content = _fetch_html_via_requests(url, timeout=30)

            if not content:
                return None

            soup = BeautifulSoup(content, 'lxml')
            
            all_odds = {}
            # Busca direta nas tabelas de odds
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
                'all_odds': all_odds, 'source': 'oddsportal',
                'source_url': url
            }
        except Exception as e: 
            return None

# OTIMIZAÇÃO 5 — Alerta de velocidade e medição
def fetch_games_sync() -> list:
    start_time = time.time()
    try:
        scraper = OddsPortalScraper()
        games = asyncio.run(scraper.fetch_games_with_odds())
        elapsed = time.time() - start_time
        
        logger.info(f"[OddsPortal] Coleta concluída em {elapsed:.1f}s | Jogos: {len(games)}")
        
        if elapsed > 90:
            send_message(f"⚠️ *Scraper Lento*: {elapsed:.1f}s detectados. Meta < 60s.")
            
        return games
    except Exception as e:
        logger.error(f"Erro crítico no fetch_games_sync: {e}")
        return []
