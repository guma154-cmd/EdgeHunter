"""
EdgeHunter — Modelo para estatísticas de Surebet (Auto-aprendizado)
"""
from datetime import datetime
from app import db

class SurebetStat(db.Model):
    __tablename__ = 'surebet_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    bookmaker_pair = db.Column(db.String(100), nullable=False) # ex: "bet365_betano"
    league = db.Column(db.String(100), nullable=False)
    
    avg_profit_pct = db.Column(db.Float, default=0.0)
    total_opportunities = db.Column(db.Integer, default=0)
    avg_window_minutes = db.Column(db.Float, default=0.0) # tempo médio disponível
    
    last_detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def update_stats(cls, book_A: str, book_B: str, league: str, profit_pct: float):
        pair = "_".join(sorted([book_A.lower(), book_B.lower()]))
        stat = cls.query.filter_by(bookmaker_pair=pair, league=league).first()
        
        if not stat:
            stat = cls(bookmaker_pair=pair, league=league)
            db.session.add(stat)
        
        # Média móvel simples para lucro
        stat.avg_profit_pct = (stat.avg_profit_pct * stat.total_opportunities + profit_pct) / (stat.total_opportunities + 1)
        stat.total_opportunities += 1
        stat.last_detected_at = datetime.utcnow()
        db.session.commit()

class Surebet(db.Model):
    __tablename__ = 'surebets'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    
    bookmaker_A = db.Column(db.String(50), nullable=False)
    outcome_A = db.Column(db.String(20), nullable=False)
    odds_A = db.Column(db.Float, nullable=False)
    stake_A = db.Column(db.Float, nullable=False)
    
    bookmaker_B = db.Column(db.String(50), nullable=False)
    outcome_B = db.Column(db.String(20), nullable=False)
    odds_B = db.Column(db.Float, nullable=False)
    stake_B = db.Column(db.Float, nullable=False)
    
    total_stake = db.Column(db.Float, nullable=False)
    profit_pct = db.Column(db.Float, nullable=False)
    guaranteed_profit = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(20), default='pending') # pending, settled
    alert_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
