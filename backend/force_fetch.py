import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from app import create_app

app = create_app()
with app.app_context():
    from app.data.scheduler import _fetch_odds_task
    print('Iniciando _fetch_odds_task...')
    _fetch_odds_task(app)
    print('_fetch_odds_task finalizado')
