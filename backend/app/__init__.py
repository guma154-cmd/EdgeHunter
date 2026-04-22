"""
EdgeHunter — Flask Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Configuração
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])
    
    # Blueprints
    from app.routes.games import games_bp
    from app.routes.bets import bets_bp
    from app.routes.analytics import analytics_bp
    from app.routes.models import models_bp
    
    app.register_blueprint(games_bp, url_prefix='/api/games')
    app.register_blueprint(bets_bp, url_prefix='/api/bets')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(models_bp, url_prefix='/api/models')
    
    # Health check
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0'}
    
    return app
