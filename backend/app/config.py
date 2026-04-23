"""
EdgeHunter — Configurações da Aplicação
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..', '..'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(project_root, "database", "edgehunter.db")}')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # APIs
    ODDS_API_KEY = os.environ.get('ODDS_API_KEY', '')
    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY', '')
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
    APIFOOTBALL_KEY = os.environ.get('APIFOOTBALL_KEY', '')
    ODDS_API_BASE_URL = 'https://api.the-odds-api.com/v4'
    FOOTBALL_DATA_BASE_URL = 'https://api.football-data.org/v4'
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

    # AI Engine
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GROQ_API_KEY   = os.environ.get('GROQ_API_KEY', '')
    
    # Engine Parameters
    MIN_EDGE_PCT = float(os.environ.get('MIN_EDGE_PCT', 3.0))
    MIN_SUREBET_PROFIT = float(os.environ.get('MIN_SUREBET_PROFIT', 1.0))
    PAPER_TRADING_STAKE = float(os.environ.get('PAPER_TRADING_STAKE', 10.0))
    ROLLING_WINDOW_DAYS = int(os.environ.get('ROLLING_WINDOW_DAYS', 30))
    DRIFT_THRESHOLD = float(os.environ.get('DRIFT_THRESHOLD', 0.05))
    AB_TEST_MIN_BETS = int(os.environ.get('AB_TEST_MIN_BETS', 50))
    
    # Bookmakers
    SHARP_BOOK = os.environ.get('SHARP_BOOK', 'pinnacle')
    SOFT_BOOKS = os.environ.get('SOFT_BOOKS', 'bet365,betano,superbet').split(',')
    
    # Scheduler
    ODDS_FETCH_INTERVAL_MINUTES = int(os.environ.get('ODDS_FETCH_INTERVAL_MINUTES', 15))
    RESULT_CHECK_INTERVAL_MINUTES = int(os.environ.get('RESULT_CHECK_INTERVAL_MINUTES', 30))
    RETRAIN_HOUR = int(os.environ.get('RETRAIN_HOUR', 4))
    
    # Modelos e pesos iniciais
    INITIAL_MODEL_WEIGHTS = {
        'dixon_coles': 0.30,
        'elo': 0.20,
        'xgboost': 0.35,
        'bayesian': 0.15
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
