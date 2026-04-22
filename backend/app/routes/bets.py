"""
EdgeHunter — Rotas de Apostas (Bets)
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Bet, Game
from datetime import datetime, timedelta
import numpy as np

bets_bp = Blueprint('bets', __name__)


@bets_bp.route('/', methods=['GET'])
def list_bets():
    """Lista apostas com filtros opcionais."""
    result = request.args.get('result')  # pending, won, lost
    days = int(request.args.get('days', 30))
    limit = int(request.args.get('limit', 50))
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = Bet.query.filter(Bet.timestamp >= cutoff)
    
    if result:
        query = query.filter_by(result=result)
    
    bets = query.order_by(Bet.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'bets': [b.to_dict() for b in bets],
        'total': query.count()
    })


@bets_bp.route('/pending', methods=['GET'])
def pending_bets():
    """Apostas pendentes de resultado."""
    bets = Bet.query.filter_by(result='pending').order_by(Bet.timestamp.desc()).all()
    
    return jsonify({
        'bets': [b.to_dict() for b in bets],
        'count': len(bets)
    })


@bets_bp.route('/stats', methods=['GET'])
def bet_stats():
    """Estatísticas gerais das apostas."""
    days = int(request.args.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    all_bets = Bet.query.filter(Bet.timestamp >= cutoff).all()
    settled = [b for b in all_bets if b.result in ['won', 'lost']]
    
    if not settled:
        return jsonify({'message': 'Sem apostas liquidadas no período'})
    
    rois = [b.roi for b in settled if b.roi is not None]
    clvs = [b.clv for b in settled if b.clv is not None]
    profits = [b.profit_loss for b in settled if b.profit_loss is not None]
    
    wins = sum(1 for b in settled if b.result == 'won')
    losses = sum(1 for b in settled if b.result == 'lost')
    
    sharpe = 0.0
    if len(rois) > 1:
        std = np.std(rois)
        if std > 0:
            sharpe = np.mean(rois) / std
    
    # ROI por liga
    roi_by_league = {}
    for bet in settled:
        game = Game.query.get(bet.game_id)
        if game:
            league = game.league
            if league not in roi_by_league:
                roi_by_league[league] = []
            if bet.roi is not None:
                roi_by_league[league].append(bet.roi)
    
    roi_by_league_avg = {
        league: round(np.mean(rois_l), 2)
        for league, rois_l in roi_by_league.items()
        if rois_l
    }
    
    # ROI por seleção
    roi_by_selection = {}
    for sel in ['home', 'draw', 'away']:
        sel_bets = [b for b in settled if b.selection == sel and b.roi is not None]
        if sel_bets:
            roi_by_selection[sel] = round(np.mean([b.roi for b in sel_bets]), 2)
    
    return jsonify({
        'period_days': days,
        'total_bets': len(all_bets),
        'settled': len(settled),
        'pending': len(all_bets) - len(settled),
        'wins': wins,
        'losses': losses,
        'win_rate': round(wins / len(settled) * 100, 1) if settled else 0,
        'total_profit': round(sum(profits), 2),
        'roi_avg': round(np.mean(rois), 2) if rois else 0,
        'roi_total': round(sum(profits) / sum(b.stake for b in settled) * 100, 2) if settled else 0,
        'sharpe_ratio': round(sharpe, 3),
        'clv_avg': round(np.mean(clvs), 3) if clvs else 0,
        'clv_positive_rate': round(sum(1 for c in clvs if c > 0) / len(clvs) * 100, 1) if clvs else 0,
        'avg_edge': round(np.mean([b.edge_pct for b in all_bets]), 2),
        'roi_by_league': roi_by_league_avg,
        'roi_by_selection': roi_by_selection
    })


@bets_bp.route('/<int:bet_id>', methods=['GET'])
def get_bet(bet_id):
    """Detalhes de uma aposta específica."""
    bet = Bet.query.get_or_404(bet_id)
    result = bet.to_dict()
    
    # Adicionar info do jogo
    game = Game.query.get(bet.game_id)
    if game:
        result['game'] = game.to_dict()
    
    return jsonify(result)


@bets_bp.route('/clv', methods=['GET'])
def clv_analysis():
    """Análise de CLV (Closing Line Value)."""
    days = int(request.args.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    bets_with_clv = Bet.query.filter(
        Bet.timestamp >= cutoff,
        Bet.clv.isnot(None)
    ).all()
    
    if not bets_with_clv:
        return jsonify({'message': 'Sem dados de CLV disponíveis'})
    
    clvs = [b.clv for b in bets_with_clv]
    
    # Distribuição por faixas
    distribution = {
        'negative': sum(1 for c in clvs if c < 0),
        'zero_to_2': sum(1 for c in clvs if 0 <= c < 2),
        'two_to_5': sum(1 for c in clvs if 2 <= c < 5),
        'above_5': sum(1 for c in clvs if c >= 5)
    }
    
    return jsonify({
        'avg_clv': round(np.mean(clvs), 3),
        'median_clv': round(np.median(clvs), 3),
        'positive_rate': round(sum(1 for c in clvs if c > 0) / len(clvs) * 100, 1),
        'total': len(clvs),
        'distribution': distribution,
        'trend': [round(c, 2) for c in clvs[-20:]]  # últimos 20
    })
