import asyncio
import aiohttp
import logging
from difflib import SequenceMatcher
from playwright.async_api import async_playwright
from playwright_stealth import stealth

logger = logging.getLogger(__name__)

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

# --- PINNACLE ---
async def scrape_pinnacle(league_ids=[1980, 1456, 2627]) -> list:
    """Scraper para Pinnacle via API pública não documentada."""
    results = []
    headers = {
        "X-API-Key": "CmX2KcMrRmaAjNgj",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.pinnacle.com/"
    }
    
    async with aiohttp.ClientSession() as session:
        for lid in league_ids:
            try:
                # 1. Matchups
                url = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups"
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200: continue
                    matchups = await resp.json()
                
                # 2. Markets (Straight) - Contém ML, Spread e Totals
                url_markets = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight"
                async with session.get(url_markets, headers=headers) as resp:
                    if resp.status != 200: continue
                    markets = await resp.json()
                
                # Mapear markets por matchupId
                # Filtramos mercado Moneyline (type='moneyline') do período 0
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
                    
                    # Extrair times dos participants
                    home_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'home'), "Unknown")
                    away_team = next((p['name'] for p in m['participants'] if p['alignment'] == 'away'), "Unknown")
                    
                    odds = {}
                    for p in prices:
                        desig = p.get('designation') or p.get('alignment')
                        price_dec = american_to_decimal(p['price'])
                        if desig == 'home': odds['1'] = price_dec
                        elif desig == 'away': odds['2'] = price_dec
                        elif desig == 'draw': odds['X'] = price_dec
                    
                    if odds:
                        results.append({
                            "home_team": home_team,
                            "away_team": away_team,
                            "all_odds": {"pinnacle": odds}
                        })
            except Exception as e:
                logger.error(f"Erro Pinnacle (league {lid}): {e}")
    return results

# --- BETANO ---
async def scrape_betano(league_ids=[72, 5, 45]) -> list:
    """Scraper para Betano via API interna."""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://br.betano.com/",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest"
    }
    async with aiohttp.ClientSession() as session:
        for lid in league_ids:
            try:
                # Adicionar um pequeno atraso para evitar 403
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
                                if name == '1' or 'casa' in name: odds['1'] = sel.get('price')
                                elif name == '2' or 'fora' in name: odds['2'] = sel.get('price')
                                elif name == 'x' or 'empate' in name: odds['X'] = sel.get('price')
                            
                            if odds:
                                results.append({
                                    "home_team": ev.get('home'),
                                    "away_team": ev.get('away'),
                                    "all_odds": {"betano": odds}
                                })
            except Exception as e:
                logger.error(f"Erro Betano (league {lid}): {e}")
    return results

# --- BET365 ---
async def scrape_bet365() -> list:
    """Scraper para Bet365 usando Playwright (Simples)."""
    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await context.new_page()
            await stealth(page)
            
            # URL de futebol principal ou liga específica
            await page.goto("https://www.bet365.com.br/#/AC/B1/C1/D8/", wait_until="networkidle")
            await page.wait_for_timeout(5000) # Esperar renderizar odds
            
            # Exemplo de extração básica (seletores variam muito no bet365)
            # Como a bet365 é complexa, faremos uma tentativa de pegar os blocos de odds
            games_elements = await page.query_selector_all(".gl-MarketGroup")
            for game in games_elements:
                try:
                    text = await game.inner_text()
                    lines = text.split('\n')
                    # Lógica simplificada: procurar por padrões de times e odds
                    # NOTA: Em produção, isso precisa de seletores CSS muito específicos
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
    """Coleta odds das 3 casas em paralelo e faz o matching."""
    logger.info("Iniciando coleta direta...")
    
    from app.data.oddsportal_scraper import fetch_games_sync
    import asyncio
    
    # Rodar scrapers em paralelo
    tasks = [
        scrape_pinnacle(),
        scrape_betano(),
        asyncio.to_thread(fetch_games_sync) # OddsPortal como fallback de overlap
    ]
    
    scraped_data = await asyncio.gather(*tasks, return_exceptions=True)
    
    pinnacle_games = scraped_data[0] if not isinstance(scraped_data[0], Exception) else []
    betano_games = scraped_data[1] if not isinstance(scraped_data[1], Exception) else []
    oddsportal_games = scraped_data[2] if not isinstance(scraped_data[2], Exception) else []
    
    # Consolidar todas as fontes
    all_sources = [pinnacle_games, betano_games, oddsportal_games]
    combined = []
    
    # Usar Pinnacle como base e buscar matches nas outras
    for p_game in pinnacle_games:
        # Match com Betano
        m_betano = find_matching_game(p_game, betano_games)
        if m_betano: p_game['all_odds'].update(m_betano['all_odds'])
        
        # Match com OddsPortal
        m_op = find_matching_game(p_game, oddsportal_games)
        if m_op: p_game['all_odds'].update(m_op['all_odds'])
        
        combined.append(p_game)
            
    # Adicionar jogos das outras fontes que não estão na Pinnacle
    for other_list in [betano_games, oddsportal_games]:
        for g in other_list:
            if not find_matching_game(g, combined):
                combined.append(g)
            
    logger.info(f"Coleta consolidada finalizada: {len(combined)} jogos.")
    return combined

def fetch_direct_sync() -> list:
    try:
        return asyncio.run(fetch_all_direct())
    except Exception as e:
        logger.error(f"Erro no fetch_direct_sync: {e}")
        return []
