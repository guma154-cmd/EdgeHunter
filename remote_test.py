
import asyncio
import sys, os

sys.path.insert(0, '/app')
os.chdir('/app')

from app.data.direct_scrapers import scrape_pinnacle_tennis

async def test():
    try:
        print('Iniciando teste de scraping da Pinnacle Tennis no servidor...')
        games = await scrape_pinnacle_tennis()
        print(f'Jogos encontrados: {len(games)}')
        for g in games[:5]:
            print(f"  {g['home_team']} vs {g['away_team']} | Casas: {list(g['all_odds'].keys())}")
    except Exception as e:
        print(f"ERRO NO SCRAPING PINNACLE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
