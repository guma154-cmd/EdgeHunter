"""
EdgeHunter — Rotas de Jogos (Games)
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Game, Prediction
from datetime import datetime, timedelta

games_bp = Blueprint('games', __name__)


@games_bp.route('/', methods=['GET'])
def list_games():
    """Lista jogos com filtros."""
    status = request.args.get('status', 'scheduled')
    league = request.args.get('league')
    days_ahead = int(request.args.get('days_ahead', 7))
    
    query = Game.query
    
    if status == 'scheduled':
        query = query.filter(
            Game.status == 'scheduled',
            Game.match_date >= datetime.utcnow(),
            Game.match_date <= datetime.utcnow() + timedelta(days=days_ahead)
        )
    elif status:
        query = query.filter_by(status=status)
    
    if league:
        query = query.filter(Game.league.ilike(f'%{league}%'))
    
    games = query.order_by(Game.match_date).limit(100).all()
    
    return jsonify({
        'games': [g.to_dict() for g in games],
        'total': len(games)
    })


@games_bp.route('/<int:game_id>', methods=['GET'])
def get_game(game_id):
    """Detalhes completos de um jogo."""
    game = Game.query.get_or_404(game_id)
    result = game.to_dict()
    
    # Última previsão
    prediction = Prediction.query.filter_by(game_id=game_id).order_by(
        Prediction.created_at.desc()
    ).first()
    
    if prediction:
        result['prediction'] = prediction.to_dict()
    
    return jsonify(result)


@games_bp.route('/upcoming', methods=['GET'])
def upcoming_games():
    """Jogos nas próximas 24h."""
    now = datetime.utcnow()
    tomorrow = now + timedelta(hours=24)
    
    games = Game.query.filter(
        Game.match_date >= now,
        Game.match_date <= tomorrow,
        Game.status == 'scheduled'
    ).order_by(Game.match_date).all()
    
    return jsonify({
        'games': [g.to_dict() for g in games],
        'count': len(games)
    })


@games_bp.route('/leagues', methods=['GET'])
def list_leagues():
    """Lista ligas disponíveis."""
    from sqlalchemy import func
    leagues = db.session.query(
        Game.league,
        func.count(Game.id).label('count')
    ).group_by(Game.league).all()
    
    return jsonify({
        'leagues': [{'name': l, 'count': c} for l, c in leagues]
    })


@games_bp.route('/<int:game_id>/predict', methods=['POST'])
def predict_game(game_id):
    """Gera previsão manual para um jogo."""
    game = Game.query.get_or_404(game_id)
    
    try:
        from app.engine.ensemble import _get_global_ensemble
        ensemble = _get_global_ensemble()
        
        if not ensemble or not ensemble.is_ready:
            return jsonify({'error': 'Modelo não treinado'}), 503
        
        prediction = ensemble.predict(
            game.home_team,
            game.away_team,
            game.match_date.isoformat() if game.match_date else None
        )
        
        return jsonify(prediction)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
