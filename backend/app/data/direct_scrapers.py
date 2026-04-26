import asyncio
import aiohttp
import logging
import random
from difflib import SequenceMatcher
from playwright.async_api import async_playwright
from playwright_stealth import stealth

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# --- UTILS ---
def match_teams(name1: str, name2: str) -> float:
    if not name1 or not name2: return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

def find_matching_game(game_A, games_list) -> dict:
    for g in games_list:
        h_score = match_teams(game_A['home_team'], g['home_team'])
        a_score = match_teams(game_A['away_team'], g['away_team'])
        if h_score > 0.7 and a_score > 0.7:
            return g
    return None

def match_games_between_sources(games_list):
    """Agrupa jogos da mesma partida de diferentes fontes."""
    combined = []
    processed_indices = set()
    
    for i, g1 in enumerate(games_list):
        if i in processed_indices: continue
        
        current_game = g1.copy()
        for j, g2 in enumerate(games_list):
            if i == j or j in processed_indices: continue
            
            h_score = match_teams(g1['home_team'], g2['home_team'])
            a_score = match_teams(g1['away_team'], g2['away_team'])
            
            if h_score > 0.7 and a_score > 0.7:
                current_game['all_odds'].update(g2['all_odds'])
                processed_indices.add(j)
        
        combined.append(current_game)
        processed_indices.add(i)
    return combined

# --- PINNACLE ---
async def scrape_pinnacle(league_ids=[1980, 1456, 2627]) -> list:
    """Scraper para Pinnacle via API pública não documentada (Futebol)."""
    results = []
    headers = {
        "X-API-Key": "CmX2KcMrRmaAjNgj",
        "Content-Type": "application/json",
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.pinnacle.com/"
    }
    
    async with aiohttp.ClientSession() as session:
        for lid in league_ids:
            try:
                url = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups"
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200: continue
                    matchups = await resp.json()
                
                url_markets = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight"
                async with session.get(url_markets, headers=headers) as resp:
                    if resp.status != 200: continue
                    markets = await resp.json()
                
                market_map = {}
                for mkt in markets:
                    if mkt.get('type') == 'moneyline' and mkt.get('period') == 0:
                        market_map[mkt['matchupId']] = mkt
                
                for m in matchups:
                    if m.get('type') != 'matchup': continue
                    mkt = market_map.get(m['id'])
                    if not mkt: continue
                    
                    prices = mkt.get('prices', [])
                    if len(prices) < 2: continue
                    
                    home_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'home'), "Unknown")
                    away_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'away'), "Unknown")
                    
                    odds = {}
                    for p in prices:
                        desig = p.get('designation') or p.get('alignment')
                        price_dec = american_to_decimal(p['price'])
                        if desig == 'home': odds['home'] = price_dec
                        elif desig == 'away': odds['away'] = price_dec
                        elif desig == 'draw': odds['draw'] = price_dec
                    
                    if odds:
                        results.append({
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": f"Football_{lid}",
                            "sport": "football",
                            "match_date": m.get('startTime', ''),
                            "source": "pinnacle_direct",
                            "all_odds": {"pinnacle": odds}
                        })
            except Exception as e:
                logger.error(f"Erro Pinnacle (league {lid}): {e}")
    return results

async def scrape_pinnacle_tennis() -> list:
    """Coleta odds de tênis da Pinnacle."""
    # Incluindo mais ligas: ATP, WTA, Challenger, ITF
    TENNIS_LEAGUE_IDS = [368, 379, 578, 1146, 2190, 2642]
    games = []
    headers = {
        "X-API-Key": "CmX2KcMrRmaAjNgj",
        "Content-Type": "application/json",
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.pinnacle.com/"
    }
    
    async with aiohttp.ClientSession() as session:
        for lid in TENNIS_LEAGUE_IDS:
            try:
                await asyncio.sleep(0.5)
                url = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups"
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status != 200: continue
                    matchups = await resp.json()
                
                url_markets = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight"
                async with session.get(url_markets, headers=headers, timeout=15) as resp:
                    if resp.status != 200: continue
                    markets = await resp.json()
                
                market_map = {}
                for mkt in markets:
                    if mkt.get('type') == 'moneyline' and mkt.get('period') == 0:
                        market_map[mkt['matchupId']] = mkt
                
                for m in matchups:
                    if m.get('type') != 'matchup': continue
                    mkt = market_map.get(m['id'])
                    if not mkt: continue
                    
                    prices = mkt.get('prices', [])
                    if len(prices) < 2: continue
                    
                    try:
                        home_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'home'), "Unknown")
                        away_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'away'), "Unknown")
                    except: continue
                    
                    odds = {}
                    for p in prices:
                        desig = p.get('designation') or p.get('alignment')
                        price_dec = american_to_decimal(p['price'])
                        if desig == 'home': odds['home'] = price_dec
                        elif desig == 'away': odds['away'] = price_dec
                    
                    if len(odds) >= 2:
                        games.append({
                            'home_team':  home_team,
                            'away_team':  away_team,
                            'league':     f'Tennis_{lid}',
                            'sport':      'tennis',
                            'match_date': m.get('startTime',''),
                            'source':     'pinnacle_direct',
                            'all_odds': {
                                'pinnacle': odds
                            }
                        })
            except Exception as e:
                logger.error(f"[Pinnacle Tennis] Liga {lid}: {e}")
    return games

# --- BETANO ---
async def scrape_betano(league_ids=[72, 5, 45]) -> list:
    """Scraper para Betano via API interna (Futebol)."""
    results = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://br.betano.com/",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest"
    }
    async with aiohttp.ClientSession() as session:
        for lid in league_ids:
            try:
                await asyncio.sleep(1)
                url = f"https://br.betano.com/api/sports/football/?block=fixtures&competition_id={lid}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200: continue
                    data = await resp.json()
                    
                    blocks = data.get('data', {}).get('blocks', [])
                    for block in blocks:
                        events = block.get('events', [])
                        for ev in events:
                            markets = ev.get('markets', [])
                            main_market = next((m for m in markets if 'Resultado Final' in m.get('name', '')), None)
                            if not main_market: continue
                            
                            selections = main_market.get('selections', [])
                            if len(selections) < 2: continue
                            
                            odds = {}
                            for sel in selections:
                                name = sel.get('name', '').lower()
                                if name == '1' or 'casa' in name: odds['home'] = sel.get('price')
                                elif name == '2' or 'fora' in name: odds['away'] = sel.get('price')
                                elif name == 'x' or 'empate' in name: odds['draw'] = sel.get('price')
                            
                            if odds:
                                results.append({
                                    "home_team": ev.get('home'),
                                    "away_team": ev.get('away'),
                                    "league": f"Football_{lid}",
                                    "sport": "football",
                                    "match_date": ev.get('startTime', ''),
                                    "source": "betano_direct",
                                    "all_odds": {"betano": odds}
                                })
            except Exception as e:
                logger.error(f"Erro Betano (league {lid}): {e}")
    return results

async def scrape_betano_tennis() -> list:
    """Coleta odds de tênis da Betano BR."""
    games = []
    try:
        url = "https://br.betano.com/api/sports/tennis/"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://br.betano.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[Betano Tennis] Status {resp.status}")
                    return []
                data = await resp.json()
                
                blocks = data.get('data', {}).get('blocks', [])
                for block in blocks:
                    events = block.get('events', [])
                    for event in events:
                        home = event.get('home', '')
                        away = event.get('away', '')
                        markets = event.get('markets', [])
                        
                        for market in markets:
                            m_name = market.get('name','').lower()
                            if 'vencedor' in m_name or 'winner' in m_name:
                                selections = market.get('selections', [])
                                if len(selections) < 2: continue
                                
                                odds = {}
                                for sel in selections:
                                    name = sel.get('name', '').lower()
                                    if name == '1' or home.lower() in name: odds['home'] = sel.get('price')
                                    elif name == '2' or away.lower() in name: odds['away'] = sel.get('price')
                                
                                if len(odds) >= 2:
                                    games.append({
                                        'home_team':  home,
                                        'away_team':  away,
                                        'league':     'Tennis_Betano',
                                        'sport':      'tennis',
                                        'match_date': event.get('startTime',''),
                                        'source':     'betano_direct',
                                        'all_odds': {
                                            'betano': odds
                                        }
                                    })
    except Exception as e:
        logger.error(f"[Betano Tennis] Erro: {e}")
    return games

# --- BET365 ---
async def scrape_bet365() -> list:
    """Scraper para Bet365 usando Playwright (Simples)."""
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = await context.new_page()
            await stealth(page)
            
            await page.goto("https://www.bet365.com.br/#/AC/B1/C1/D8/", wait_until="networkidle")
            await page.wait_for_timeout(5000)
            
            games_elements = await page.query_selector_all(".gl-MarketGroup")
            for game in games_elements:
                try:
                    pass 
                except: continue
            
            await browser.close()
    except Exception as e:
        logger.error(f"Erro Bet365: {e}")
    return results

def american_to_decimal(amm):
    if amm > 0:
        return (amm / 100) + 1
    else:
        return (100 / abs(amm)) + 1

# --- MAIN ---
async def fetch_all_direct() -> list:
    """Coleta odds de futebol e tênis em paralelo e faz o matching."""
    logger.info("Iniciando coleta direta consolidada...")
    
    from app.data.oddsportal_scraper import fetch_games_sync
    
    tasks = [
        scrape_pinnacle(),
        scrape_betano(),
        scrape_pinnacle_tennis(),
        scrape_betano_tennis(),
        asyncio.to_thread(fetch_games_sync)
    ]
    
    scraped_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_games = []
    for r in scraped_results:
        if isinstance(r, list):
            all_games.extend(r)
        elif isinstance(r, Exception):
            logger.error(f"Erro em um dos scrapers: {r}")
            
    football_games = [g for g in all_games if g.get('sport') != 'tennis']
    tennis_games   = [g for g in all_games if g.get('sport') == 'tennis']
    
    matched_football = match_games_between_sources(football_games)
    matched_tennis = match_games_between_sources(tennis_games)
    
    combined = matched_football + matched_tennis
    logger.info(f"Coleta consolidada finalizada: {len(combined)} jogos ({len(matched_football)} futebol, {len(matched_tennis)} tênis).")
    return combined

def fetch_direct_sync() -> list:
    try:
        return asyncio.run(fetch_all_direct())
    except Exception as e:
        logger.error(f"Erro no fetch_direct_sync: {e}")
        return []
