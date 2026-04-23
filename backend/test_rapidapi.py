import os
from dotenv import load_dotenv
load_dotenv()
from app.data.rapidapi_client import RapidAPIClient

client = RapidAPIClient(os.getenv('RAPIDAPI_KEY'))
try:
    games = client.fetch_odds()
    print(f'Jogos coletados: {len(games)}')
    if games:
        print(f'Exemplo: {games[0]["home_team"]} vs {games[0]["away_team"]}')
        print(f'Casas disponíveis: {list(games[0].get("all_odds", {}).keys())}')
    else:
        print('NENHUM JOGO — verificar subscrição ou odds disponíveis')
    print(f'Requisições usadas hoje: {client.daily_requests}')
except Exception as e:
    print(f'ERRO: {e}')
