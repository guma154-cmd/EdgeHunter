import sys
import os
import logging

# Adicionar o diretório atual ao path
sys.path.append(os.getcwd())

from app.data.oddsportal_scraper import fetch_games_sync
from app.detection.surebet_detector import SurebetDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("--- Iniciando Scraping OddsPortal Ao Vivo ---")
try:
    games = fetch_games_sync()
    print(f"Jogos coletados: {len(games)}")

    detector = SurebetDetector(min_profit_pct=0.1)

    for g in games[:10]:
        print(f"\n{g['home_team']} vs {g['away_team']} | {g['league']}")
        for casa, odds in g.get('all_odds', {}).items():
            print(f"  {casa:10}: H={odds['home']:<6} D={odds['draw']:<6} A={odds['away']:<6}")
        
        opps = detector.detect(g)
        if opps:
            print(f"  *** {len(opps)} SUREBET(S) DETECTADO(S)! ***")
            best = opps[0]
            print(f"  Melhor: {best['bookmaker_A']} vs {best['bookmaker_B']} = {best['profit_pct']:.2f}% lucro")
            if best.get('is_sharp_verified'):
                print("  [✓] SHARP VERIFIED (Pinnacle confirma o valor)")
except Exception as e:
    print(f"ERRO CRÍTICO NO TESTE: {e}")

print("\n--- Teste Finalizado ---")
