"""
EdgeHunter — Rotas de Analytics e Modelos
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Bet, Game, ModelVersion, Performance
from datetime import datetime, timedelta, date
import numpy as np

analytics_bp = Blueprint('analytics', __name__)


# =========================================================
# ANALYTICS
# =========================================================

@analytics_bp.route('/overview', methods=['GET'])
def overview():
    """Dashboard principal com métricas gerais."""
    days = int(request.args.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Apostas
    all_bets = Bet.query.filter(Bet.timestamp >= cutoff).all()
    settled = [b for b in all_bets if b.result in ['won', 'lost']]
    
    rois = [b.roi for b in settled if b.roi is not None]
    clvs = [b.clv for b in settled if b.clv is not None]
    profits = [b.profit_loss for b in settled if b.profit_loss is not None]
    edges = [b.edge_pct for b in all_bets]
    
    total_stake = sum(b.stake for b in settled)
    total_profit = sum(profits)
    
    # Sharpe Ratio
    sharpe = 0.0
    if len(rois) > 1 and np.std(rois) > 0:
        sharpe = np.mean(rois) / np.std(rois)
    
    # Modelo ativo
    active_model = ModelVersion.query.filter_by(is_active=True).first()
    
    # Drift status
    from app.engine.drift import _get_global_drift_detector
    drift = _get_global_drift_detector()
    drift_status = drift.get_summary() if drift else {}
    
    return jsonify({
        'period_days': days,
        'summary': {
            'total_bets': len(all_bets),
            'settled': len(settled),
            'pending': len(all_bets) - len(settled),
            'wins': sum(1 for b in settled if b.result == 'won'),
            'losses': sum(1 for b in settled if b.result == 'lost'),
            'win_rate': round(sum(1 for b in settled if b.result == 'won') / len(settled) * 100, 1) if settled else 0
        },
        'performance': {
            'total_profit_units': round(total_profit, 2),
            'roi': round(total_profit / total_stake * 100, 2) if total_stake > 0 else 0,
            'roi_avg_per_bet': round(np.mean(rois), 2) if rois else 0,
            'sharpe_ratio': round(sharpe, 3),
            'clv_avg': round(np.mean(clvs), 3) if clvs else 0,
            'avg_edge_detected': round(np.mean(edges), 2) if edges else 0
        },
        'model': active_model.to_dict() if active_model else None,
        'drift': drift_status
    })


@analytics_bp.route('/roi-timeline', methods=['GET'])
def roi_timeline():
    """Timeline de ROI acumulado."""
    days = int(request.args.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    bets = Bet.query.filter(
        Bet.timestamp >= cutoff,
        Bet.result != 'pending'
    ).order_by(Bet.timestamp).all()
    
    cumulative = []
    running_profit = 0
    running_stake = 0
    
    for bet in bets:
        if bet.profit_loss is not None:
            running_profit += bet.profit_loss
            running_stake += bet.stake
            roi = running_profit / running_stake * 100 if running_stake > 0 else 0
            
            cumulative.append({
                'date': bet.timestamp.isoformat(),
                'cumulative_profit': round(running_profit, 2),
                'roi': round(roi, 2),
                'edge': bet.edge_pct
            })
    
    return jsonify({'timeline': cumulative})


@analytics_bp.route('/roi-by-league', methods=['GET'])
def roi_by_league():
    """ROI segmentado por liga."""
    days = int(request.args.get('days', 30))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    bets = Bet.query.filter(
        Bet.timestamp >= cutoff,
        Bet.result != 'pending'
    ).all()
    
    league_data = {}
    
    for bet in bets:
        game = Game.query.get(bet.game_id)
        if not game:
            continue
        
        league = game.league
        if league not in league_data:
            league_data[league] = {
                'bets': 0, 'wins': 0,
                'profit': 0, 'stake': 0, 'edges': []
            }
        
        league_data[league]['bets'] += 1
        if bet.result == 'won':
            league_data[league]['wins'] += 1
        if bet.profit_loss is not None:
            league_data[league]['profit'] += bet.profit_loss
        league_data[league]['stake'] += bet.stake
        league_data[league]['edges'].append(bet.edge_pct)
    
    result = []
    for league, data in league_data.items():
        roi = data['profit'] / data['stake'] * 100 if data['stake'] > 0 else 0
        result.append({
            'league': league,
            'bets': data['bets'],
            'wins': data['wins'],
            'win_rate': round(data['wins'] / data['bets'] * 100, 1),
            'roi': round(roi, 2),
            'avg_edge': round(np.mean(data['edges']), 2) if data['edges'] else 0
        })
    
    result.sort(key=lambda x: x['roi'], reverse=True)
    return jsonify({'by_league': result})


@analytics_bp.route('/edge-distribution', methods=['GET'])
def edge_distribution():
    """Distribuição do edge detectado."""
    days = int(request.args.get('days', 60))
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    bets = Bet.query.filter(Bet.timestamp >= cutoff).all()
    edges = [b.edge_pct for b in bets]
    
    if not edges:
        return jsonify({'distribution': []})
    
    # Histograma
    buckets = [
        {'range': '3-4%', 'min': 3, 'max': 4},
        {'range': '4-5%', 'min': 4, 'max': 5},
        {'range': '5-7%', 'min': 5, 'max': 7},
        {'range': '7-10%', 'min': 7, 'max': 10},
        {'range': '>10%', 'min': 10, 'max': 999}
    ]
    
    distribution = []
    for bucket in buckets:
        count = sum(1 for e in edges if bucket['min'] <= e < bucket['max'])
        settled_in_bucket = [
            b for b in bets
            if bucket['min'] <= b.edge_pct < bucket['max']
            and b.result != 'pending' and b.roi is not None
        ]
        roi = np.mean([b.roi for b in settled_in_bucket]) if settled_in_bucket else 0
        
        distribution.append({
            'range': bucket['range'],
            'count': count,
            'avg_roi': round(roi, 2)
        })
    
    return jsonify({
        'distribution': distribution,
        'total': len(bets),
        'avg_edge': round(np.mean(edges), 2)
    })
