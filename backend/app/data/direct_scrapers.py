import asyncio
import aiohttp
import logging
import random
from difflib import SequenceMatcher
from playwright.async_api import async_playwright
try:
    from playwright_stealth import Stealth
    async def apply_stealth(page): await Stealth().apply_stealth_async(page)
except:
    async def apply_stealth(page): pass

logger = logging.getLogger(__name__)

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"]

def normalize_name(n): return n.lower().replace('j.', '').replace('m.', '').strip()
def match_teams(n1, n2):
    r = SequenceMatcher(None, normalize_name(n1), normalize_name(n2)).ratio()
    if r > 0.8: return r
    if set(normalize_name(n1).split()) & set(normalize_name(n2).split()): return 0.85
    return r

def match_games_between_sources(g_list):
    res = []; proc = set()
    for i, g1 in enumerate(g_list):
        if i in proc: continue
        cur = g1.copy()
        for j, g2 in enumerate(g_list):
            if i != j and j not in proc and match_teams(g1['home_team'], g2['home_team']) > 0.7 and match_teams(g1['away_team'], g2['away_team']) > 0.7:
                cur['all_odds'].update(g2['all_odds']); proc.add(j)
        res.append(cur); proc.add(i)
    return res

def american_to_decimal(a): return (a/100)+1 if a>0 else (100/abs(a))+1

async def scrape_pinnacle_tennis():
    # IDs reais descobertos via network monitor
    res = []; lids = [199191, 233538, 1740, 1745]
    h = {"X-API-Key": "CmX2KcMrRmaAjNgj", "Content-Type": "application/json", "User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession() as s:
        for lid in lids:
            try:
                async with s.get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups", headers=h) as r:
                    if r.status != 200: continue
                    ms = await r.json()
                async with s.get(f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight", headers=h) as r:
                    if r.status != 200: continue
                    mkts = await r.json()
                m_map = {m['matchupId']: m for m in mkts if m.get('type') == 'moneyline' and m.get('period') == 0}
                for m in ms:
                    mkt = m_map.get(m['id'])
                    if not mkt or not mkt.get('prices'): continue
                    h_t = next((pa['name'] for pa in m['participants'] if pa['alignment'] == 'home'), "Home")
                    a_t = next((pa['name'] for pa in m['participants'] if pa['alignment'] == 'away'), "Away")
                    odds = {'home': american_to_decimal(next(p['price'] for p in mkt['prices'] if p.get('designation')=='home')), 'away': american_to_decimal(next(p['price'] for p in mkt['prices'] if p.get('designation')=='away'))}
                    res.append({'home_team': h_t, 'away_team': a_t, 'league': 'Tennis', 'sport': 'tennis', 'all_odds': {'pinnacle': odds}})
            except: pass
    return res

async def scrape_betano_tennis():
    res = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            page = await b.new_page(); await apply_stealth(page)
            api_data = None
            async def h_r(r):
                nonlocal api_data
                if "api/sports/tennis/?block=fixtures" in r.url and r.status == 200:
                    try: api_data = await r.json()
                    except: pass
            page.on("response", h_r)
            await page.goto("https://br.betano.com/sport/tenis/", wait_until="networkidle", timeout=60000)
            if api_data:
                for block in api_data.get('data', {}).get('blocks', []):
                    for ev in block.get('events', []):
                        h = ev.get('home', ''); a = ev.get('away', '')
                        for mkt in ev.get('markets', []):
                            if 'vencedor' in mkt.get('name','').lower():
                                sels = mkt.get('selections', [])
                                if len(sels) >= 2:
                                    res.append({'home_team': h, 'away_team': a, 'league': 'Tennis', 'sport': 'tennis', 'all_odds': {'betano': {'home': float(sels[0]['price']), 'away': float(sels[1]['price'])}}})
            await b.close()
    except: pass
    return res

async def fetch_all_direct():
    from app.data.oddsportal_scraper import fetch_games_sync
    tasks = [scrape_pinnacle_tennis(), scrape_betano_tennis(), asyncio.to_thread(fetch_games_sync)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_g = []
    for r in results:
        if isinstance(r, list): all_g.extend(r)
    fb = [g for g in all_g if g.get('sport') != 'tennis']
    tn = [g for g in all_g if g.get('sport') == 'tennis']
    return match_games_between_sources(fb) + match_games_between_sources(tn)

def fetch_direct_sync():
    try: return asyncio.run(fetch_all_direct())
    except: return []
