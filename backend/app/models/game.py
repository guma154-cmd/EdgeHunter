"""
EdgeHunter — Modelos SQLAlchemy
Games (partidas) e Predictions (previsões dos modelos)
"""
from datetime import datetime
from app import db
import json


class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True, nullable=True)  # ID da API
    league = db.Column(db.String(100), nullable=False)
    league_id = db.Column(db.String(50), nullable=True)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    match_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, live, finished
    
    # Resultado real
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    
    # Odds Pinnacle (sharp line)
    pinnacle_home = db.Column(db.Float, nullable=True)
    pinnacle_draw = db.Column(db.Float, nullable=True)
    pinnacle_away = db.Column(db.Float, nullable=True)
    pinnacle_over25 = db.Column(db.Float, nullable=True)
    pinnacle_under25 = db.Column(db.Float, nullable=True)
    
    # Odds casas soft (best available)
    soft_home = db.Column(db.Float, nullable=True)
    soft_away = db.Column(db.Float, nullable=True)
    soft_draw = db.Column(db.Float, nullable=True)
    soft_book = db.Column(db.String(50), nullable=True)
    
    # Closing line (odds no fechamento)
    closing_home = db.Column(db.Float, nullable=True)
    closing_draw = db.Column(db.Float, nullable=True)
    closing_away = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    predictions = db.relationship('Prediction', backref='game', lazy=True)
    bets = db.relationship('Bet', backref='game', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'external_id': self.external_id,
            'league': self.league,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'status': self.status,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'odds': {
                'pinnacle': {
                    'home': self.pinnacle_home,
                    'draw': self.pinnacle_draw,
                    'away': self.pinnacle_away
                },
                'soft': {
                    'home': self.soft_home,
                    'draw': self.soft_draw,
                    'away': self.soft_away,
                    'book': self.soft_book
                }
            }
        }


class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    model_version_id = db.Column(db.Integer, db.ForeignKey('model_versions.id'), nullable=True)
    
    # Probabilidades individuais de cada modelo
    dixon_coles_home = db.Column(db.Float, nullable=True)
    dixon_coles_draw = db.Column(db.Float, nullable=True)
    dixon_coles_away = db.Column(db.Float, nullable=True)
    
    elo_home = db.Column(db.Float, nullable=True)
    elo_draw = db.Column(db.Float, nullable=True)
    elo_away = db.Column(db.Float, nullable=True)
    
    xgboost_home = db.Column(db.Float, nullable=True)
    xgboost_draw = db.Column(db.Float, nullable=True)
    xgboost_away = db.Column(db.Float, nullable=True)
    
    bayesian_home = db.Column(db.Float, nullable=True)
    bayesian_draw = db.Column(db.Float, nullable=True)
    bayesian_away = db.Column(db.Float, nullable=True)
    
    # Ensemble final (após calibração)
    prob_home = db.Column(db.Float, nullable=False)
    prob_draw = db.Column(db.Float, nullable=False)
    prob_away = db.Column(db.Float, nullable=False)
    
    # Pesos usados no ensemble
    weights_json = db.Column(db.Text, nullable=True)
    
    # Calibração
    brier_score = db.Column(db.Float, nullable=True)
    calibration_error = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def weights(self):
        if self.weights_json:
            return json.loads(self.weights_json)
        return {}
    
    @weights.setter
    def weights(self, value):
        self.weights_json = json.dumps(value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'probabilities': {
                'home': round(self.prob_home, 4),
                'draw': round(self.prob_draw, 4),
                'away': round(self.prob_away, 4)
            },
            'individual_models': {
                'dixon_coles': {'home': self.dixon_coles_home, 'draw': self.dixon_coles_draw, 'away': self.dixon_coles_away},
                'elo': {'home': self.elo_home, 'draw': self.elo_draw, 'away': self.elo_away},
                'xgboost': {'home': self.xgboost_home, 'draw': self.xgboost_draw, 'away': self.xgboost_away},
                'bayesian': {'home': self.bayesian_home, 'draw': self.bayesian_draw, 'away': self.bayesian_away}
            },
            'weights': self.weights,
            'brier_score': self.brier_score,
            'created_at': self.created_at.isoformat()
        }
