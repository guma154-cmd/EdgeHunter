import pytest
pytest.importorskip("flask")
import asyncio
import logging
import sys
import os

# Adicionar o diretório atual ao path para importar app
sys.path.append(os.getcwd())

from app.data.oddsportal_scraper import fetch_games_sync

# Configurar logging para ver o que acontece
logging.basicConfig(level=logging.INFO)

print("--- Iniciando Teste de Scraping OddsPortal ---")
games = fetch_games_sync()
print(f"\nTotal jogos coletados: {len(games)}")

if not games:
    print("Aviso: Nenhum jogo coletado. Pode ser devido ao horário ou bloqueio temporário.")
else:
    for g in games[:5]:
        print(f"\nPartida: {g['home_team']} vs {g['away_team']} | Liga: {g['league']}")
        for casa, odds in g['all_odds'].items():
            print(f"  {casa:10}: H={odds['home']:<6} D={odds['draw']:<6} A={odds['away']:<6}")
        
        # Testar lógica de surebet simplificada (H vs A)
        casas = list(g['all_odds'].keys())
        for i, ca in enumerate(casas):
            for cb in casas[i+1:]:
                # Home A vs Away B
                odd_h_a = g['all_odds'][ca]['home']
                odd_a_b = g['all_odds'][cb]['away']
                if odd_h_a > 1 and odd_a_b > 1:
                    arb1 = (1/odd_h_a) + (1/odd_a_b)
                    if arb1 < 1.0:
                        print(f"  *** SUREBET DETECTADA (H-A): {ca} ({odd_h_a}) + {cb} ({odd_a_b}) | Lucro: {(1-arb1)*100:.2f}% ***")
                
                # Away A vs Home B
                odd_a_a = g['all_odds'][ca]['away']
                odd_h_b = g['all_odds'][cb]['home']
                if odd_a_a > 1 and odd_h_b > 1:
                    arb2 = (1/odd_a_a) + (1/odd_h_b)
                    if arb2 < 1.0:
                        print(f"  *** SUREBET DETECTADA (A-H): {ca} ({odd_a_a}) + {cb} ({odd_h_b}) | Lucro: {(1-arb2)*100:.2f}% ***")

print("\n--- Teste Finalizado ---")
