"""
EdgeHunter — Modelo de Apostas (Paper Trading)
"""
from datetime import datetime
from app import db


class Bet(db.Model):
    __tablename__ = 'bets'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=True)
    
    # Detalhes da aposta
    market = db.Column(db.String(20), nullable=False)   # 1X2, over, under
    selection = db.Column(db.String(20), nullable=False) # home, draw, away, over, under
    odd = db.Column(db.Float, nullable=False)            # Odd disponível (casa soft)
    bookmaker = db.Column(db.String(50), nullable=True)  # Qual casa
    stake = db.Column(db.Float, nullable=False, default=10.0)  # Unidades apostadas
    
    # Edge detectado
    our_prob = db.Column(db.Float, nullable=False)       # Nossa probabilidade estimada
    implied_prob = db.Column(db.Float, nullable=False)   # Probabilidade implícita da odd
    edge_pct = db.Column(db.Float, nullable=False)       # Edge em %
    
    # CLV (Closing Line Value)
    closing_odd = db.Column(db.Float, nullable=True)     # Odd no fechamento
    clv = db.Column(db.Float, nullable=True)             # CLV calculado
    
    # Resultado
    result = db.Column(db.String(20), default='pending') # pending, won, lost, void
    profit_loss = db.Column(db.Float, nullable=True)     # Lucro/prejuízo em unidades
    roi = db.Column(db.Float, nullable=True)             # ROI da aposta
    
    # Metadata
    is_paper = db.Column(db.Boolean, default=True)       # Paper trade ou real
    alert_sent = db.Column(db.Boolean, default=False)    # Alerta Telegram enviado
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime, nullable=True)
    
    def settle(self, home_score: int, away_score: int):
        """Resolve a aposta após o resultado do jogo."""
        self.settled_at = datetime.utcnow()
        
        won = False
        if self.market == '1X2':
            if home_score > away_score and self.selection == 'home':
                won = True
            elif home_score == away_score and self.selection == 'draw':
                won = True
            elif home_score < away_score and self.selection == 'away':
                won = True
        elif self.market == 'over_under_25':
            total = home_score + away_score
            if total > 2.5 and self.selection == 'over':
                won = True
            elif total <= 2.5 and self.selection == 'under':
                won = True
        
        if won:
            self.result = 'won'
            self.profit_loss = self.stake * (self.odd - 1)
        else:
            self.result = 'lost'
            self.profit_loss = -self.stake
        
        self.roi = (self.profit_loss / self.stake) * 100
    
    def calculate_clv(self):
        """Calcula o Closing Line Value."""
        if self.closing_odd and self.closing_odd > 0:
            self.clv = ((self.odd / self.closing_odd) - 1) * 100
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'market': self.market,
            'selection': self.selection,
            'odd': self.odd,
            'bookmaker': self.bookmaker,
            'stake': self.stake,
            'our_prob': round(self.our_prob, 4),
            'implied_prob': round(self.implied_prob, 4),
            'edge_pct': round(self.edge_pct, 2),
            'clv': round(self.clv, 2) if self.clv else None,
            'result': self.result,
            'profit_loss': round(self.profit_loss, 2) if self.profit_loss else None,
            'roi': round(self.roi, 2) if self.roi else None,
            'is_paper': self.is_paper,
            'timestamp': self.timestamp.isoformat()
        }
