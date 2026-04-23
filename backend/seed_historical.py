"""
EdgeHunter — Historical Seeder
Busca dados da Football-Data.org e treina o ModelEnsemble pela primeira vez.
"""
import sys
import os
from dotenv import load_dotenv
import logging
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import create_app, db
from app.data.football_data import FootballDataClient
from app.engine.ensemble import ModelEnsemble, _set_global_ensemble

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_seed():
    app = create_app()
    with app.app_context():
        api_key = os.environ.get('FOOTBALL_DATA_API_KEY')
        if not api_key:
            logger.error("FOOTBALL_DATA_API_KEY nao configurada no .env")
            return
        
        client = FootballDataClient(api_key)
        
        logger.info("Coletando historico da Football-Data (apenas algumas ligas/seasons para o seed rapido)...")
        current_year = datetime.datetime.now().year
        df = client.get_historical_matches_df(
            competition_codes=['PL', 'PD'], 
            seasons=[current_year - 2, current_year - 1]
        )
        
        if df.empty:
            logger.error("Nenhuma partida historica retornada!")
            return
            
        logger.info(f"Treinando ensemble com {len(df)} partidas...")
        ensemble = ModelEnsemble()
        ensemble.train(df)
        
        _set_global_ensemble(ensemble, challenger=False)
        logger.info("Seed historico concluido com sucesso!")

if __name__ == '__main__':
    run_seed()
