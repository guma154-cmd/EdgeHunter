"""
EdgeHunter — Modelos de Versão e Performance
Rastreia histórico dos modelos e métricas de performance
"""
from datetime import datetime
from app import db
import json


class ModelVersion(db.Model):
    __tablename__ = 'model_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False)  # ex: "v1.2.0"
    description = db.Column(db.Text, nullable=True)
    
    # Pesos do ensemble
    weights_json = db.Column(db.Text, nullable=False)
    
    # Métricas de avaliação
    brier_score = db.Column(db.Float, nullable=True)
    sharpe_ratio = db.Column(db.Float, nullable=True)
    roi_30d = db.Column(db.Float, nullable=True)
    clv_avg = db.Column(db.Float, nullable=True)
    total_bets = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=False)    # Modelo em produção
    is_champion = db.Column(db.Boolean, default=False)  # Ganhou A/B test
    ab_status = db.Column(db.String(20), default='candidate')  # candidate, testing, champion, retired
    
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    promoted_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    predictions = db.relationship('Prediction', backref='model_version_obj', lazy=True)
    performances = db.relationship('Performance', backref='model_version', lazy=True)
    
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
            'version': self.version,
            'weights': self.weights,
            'metrics': {
                'brier_score': self.brier_score,
                'sharpe_ratio': self.sharpe_ratio,
                'roi_30d': self.roi_30d,
                'clv_avg': self.clv_avg,
                'total_bets': self.total_bets
            },
            'status': {
                'is_active': self.is_active,
                'is_champion': self.is_champion,
                'ab_status': self.ab_status
            },
            'trained_at': self.trained_at.isoformat(),
            'promoted_at': self.promoted_at.isoformat() if self.promoted_at else None
        }


class Performance(db.Model):
    __tablename__ = 'performances'
    
    id = db.Column(db.Integer, primary_key=True)
    model_version_id = db.Column(db.Integer, db.ForeignKey('model_versions.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Métricas diárias
    bets_count = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    roi = db.Column(db.Float, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)
    
    # Métricas de qualidade
    brier_score = db.Column(db.Float, nullable=True)
    clv_avg = db.Column(db.Float, nullable=True)
    
    # Rolling 30d (calculado no momento)
    sharpe_30d = db.Column(db.Float, nullable=True)
    roi_30d = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'date': self.date.isoformat(),
            'bets_count': self.bets_count,
            'wins': self.wins,
            'losses': self.losses,
            'roi': self.roi,
            'profit_loss': self.profit_loss,
            'brier_score': self.brier_score,
            'clv_avg': self.clv_avg,
            'sharpe_30d': self.sharpe_30d,
            'roi_30d': self.roi_30d
        }
