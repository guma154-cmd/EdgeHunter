import os
from dotenv import load_dotenv
load_dotenv()
from app.data.oddsapiio_client import OddsApiIoClient

client = OddsApiIoClient(os.getenv('ODDSAPIIO_KEY'))
try:
    print(f"Testando com chave: {os.getenv('ODDSAPIIO_KEY')[:10]}...")
    games = client.fetch_games_with_odds()
    print(f'Jogos: {len(games)}')
    if games:
        g = games[0]
        print(f'{g["home_team"]} vs {g["away_team"]}')
        print(f'Casas: {list(g["all_odds"].keys())}')
    else:
        print("NENHUM JOGO — verifique se há jogos de soccer hoje ou se a chave é válida.")
except Exception as e:
    print(f'ERRO: {e}')
