"""
EdgeHunter — Scheduler de tarefas automáticas
APScheduler gerencia todas as tarefas periódicas do sistema.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import json
import logging
import pytz
from datetime import datetime, date, timedelta
import numpy as np

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=pytz.UTC)
    return _scheduler


def start_scheduler(app):
    """Inicializa e registra todas as tarefas agendadas."""
    scheduler = get_scheduler()
    
    # Inicializar e carregar BankrollManager
    from app.engine.bankroll_manager import BankrollManager
    bm = BankrollManager()
    bm.load_from_db(app)
    
    with app.app_context():
        from flask import current_app
        
        odds_interval = current_app.config.get('ODDS_FETCH_INTERVAL_MINUTES', 15)
        result_interval = current_app.config.get('RESULT_CHECK_INTERVAL_MINUTES', 30)
        retrain_hour = current_app.config.get('RETRAIN_HOUR', 4)
    
    # Tarefa 1: Buscar odds (a cada 15 min)
    scheduler.add_job(
        func=lambda: _fetch_odds_task(app),
        trigger=IntervalTrigger(minutes=odds_interval),
        id='fetch_odds',
        name='Buscar Odds',
        replace_existing=True
    )
    
    # Tarefa 2: Verificar resultados e liquidar apostas (a cada 30 min)
    scheduler.add_job(
        func=lambda: _check_results_task(app),
        trigger=IntervalTrigger(minutes=result_interval),
        id='check_results',
        name='Verificar Resultados',
        replace_existing=True
    )
    
    # Tarefa 3: Retraining diário (4h UTC)
    scheduler.add_job(
        func=lambda: _daily_retrain_task(app),
        trigger=CronTrigger(hour=retrain_hour, minute=0),
        id='daily_retrain',
        name='Retraining Diário',
        replace_existing=True
    )
    
    # Tarefa 4: Resumo diário Telegram (22h UTC)
    scheduler.add_job(
        func=lambda: _daily_summary_task(app),
        trigger=CronTrigger(hour=22, minute=0),
        id='daily_summary',
        name='Resumo Diário',
        replace_existing=True
    )
    
    # Tarefa 5: Atualizar métricas de performance (a cada 6h)
    scheduler.add_job(
        func=lambda: _update_metrics_task(app),
        trigger=IntervalTrigger(hours=6),
        id='update_metrics',
        name='Atualizar Métricas',
        replace_existing=True
    )

    scheduler.add_job(
        func=lambda: _autotuner_task(app),
        trigger=CronTrigger(hour=6, minute=0),
        id='autotuner',
        name='AutoTuner Paramétrico',
        replace_existing=True
    )
    
    # Heartbeat a cada 2 horas
    scheduler.add_job(
        func=lambda: _heartbeat_task(app),
        trigger=IntervalTrigger(hours=2),
        id='heartbeat',
        name='Heartbeat Telegram',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"[OK] Scheduler: {len(scheduler.get_jobs())} jobs ativos")
    
    # Envio imediato do primeiro heartbeat
    try:
        _heartbeat_task(app)
    except Exception as e:
        logger.error(f"Erro no heartbeat inicial: {e}")
        
    return scheduler


def _quick_confirm(opp: dict, games: list[dict]) -> bool:
    """Confirma se o jogo ainda está presente no lote atual sem novo scrape."""
    return any(
        g.get('home_team') == opp.get('home_team') and
        g.get('away_team') == opp.get('away_team')
        for g in games
    )


def _fetch_odds_task(app):
    """Busca novas odds e detecta value bets."""
    with app.app_context():
        try:
            from flask import current_app
            from app.models import Game, Surebet
            from app import db
            from app.alerts.telegram_bot import send_surebet_alert
            from app.detection.surebet_detector import SurebetDetector
            from app.engine.bankroll_manager import BankrollManager
            
            bm = BankrollManager()
            games = []
            source = None

            if app.config.get('BOLTODDS_API_KEY'):
                from app.data.boltodds_client import fetch_games_boltodds

                games = fetch_games_boltodds(
                    app.config['BOLTODDS_API_KEY'],
                    duration=20
                )
                if games:
                    source = 'boltodds'
                    logger.info(f"[Odds] BoltOdds: {len(games)} jogos")

            if not games and app.config.get('ODDS_API_KEY'):
                from app.data.odds_api import OddsAPIClient

                api_games = OddsAPIClient(app.config['ODDS_API_KEY']).fetch_all_value_games()
                games = [
                    {
                        'home_team': g['home_team'],
                        'away_team': g['away_team'],
                        'league': g['league'],
                        'match_date': g['match_date'],
                        'source': 'odds_api',
                        'all_odds': g.get('soft_odds', {}),
                    }
                    for g in api_games
                    if len(g.get('soft_odds', {})) >= 2
                ]
                if games:
                    source = 'odds_api'
                    logger.info(f"[Odds] The Odds API: {len(games)} jogos")

            if not games:
                from app.data.oddsportal_scraper import fetch_games_sync

                games = fetch_games_sync()
                if games:
                    source = 'oddsportal'

            logger.info(f"[Odds] {len(games)} jogos coletados")
            if not games:
                logger.warning("[Odds] Nenhum jogo - todas as fontes falharam")
                return
            
            detector = SurebetDetector(
                min_profit_pct=current_app.config.get('MIN_SUREBET_PROFIT', 1.0),
                max_profit_pct=current_app.config.get('MAX_SUREBET_ROI', 8.0),
                stake_pct=current_app.config.get('STAKE_PCT', 0.25),
                bankroll_per_book=current_app.config.get('BANKROLL_PER_BOOK', 20.0)
            )
            
            new_bets = 0
            
            # PRIMEIRA DETECÇÃO
            initial_opportunities = []
            for game_data in games:
                opps = detector.detect(game_data)
                initial_opportunities.extend(opps)

            if not initial_opportunities:
                logger.info("[Odds] 0 oportunidades detectadas")
                return

            # CONFIRMAÇÃO RÁPIDA E FILTRO DE BANCA
            confirmed_opportunities = []
            for opp in initial_opportunities:
                # 1. Verificar se tem banca para cobrir
                if not bm.can_cover(opp['bookmaker_A'], opp['stake_A'], 
                                   opp['bookmaker_B'], opp['stake_B']):
                    logger.info(f"Surebet ignorada por falta de banca: {opp['bookmaker_A']}/{opp['bookmaker_B']}")
                    continue
                
                # 2. Confirmar no lote atual em vez de aguardar novo scrape
                if _quick_confirm(opp, games):
                    confirmed_opportunities.append(opp)

            for opp in confirmed_opportunities:
                # Checar ou criar jogo no banco
                game = Game.query.filter_by(
                    home_team=opp['home_team'],
                    away_team=opp['away_team'],
                    league=opp['league']
                ).first()
                
                if not game:
                    try:
                        dt_str = opp['match_date'].replace(' ', 'T')
                        match_dt = datetime.fromisoformat(dt_str)
                    except:
                        match_dt = datetime.utcnow()

                    game = Game(
                        home_team=opp['home_team'],
                        away_team=opp['away_team'],
                        league=opp['league'],
                        match_date=match_dt,
                        status='scheduled'
                    )
                    db.session.add(game)
                    db.session.flush()
                
                # Verificar se já existe essa surebet
                existing = Surebet.query.filter_by(
                    game_id=game.id,
                    bookmaker_A=opp['bookmaker_A'],
                    bookmaker_B=opp['bookmaker_B'],
                    outcome_A=opp['outcome_A']
                ).first()
                
                if not existing:
                    surebet = Surebet(
                        game_id=game.id,
                        bookmaker_A=opp['bookmaker_A'],
                        outcome_A=opp['outcome_A'],
                        odds_A=opp['odds_A'],
                        stake_A=opp['stake_A'],
                        bookmaker_B=opp['bookmaker_B'],
                        outcome_B=opp['outcome_B'],
                        odds_B=opp['odds_B'],
                        stake_B=opp['stake_B'],
                        total_stake=opp['total_stake'],
                        profit_pct=opp['profit_pct'],
                        guaranteed_profit=opp['guaranteed_profit']
                    )
                    db.session.add(surebet)
                    
                    # Atualizar BankrollManager (deduzir stakes)
                    bm.update(opp['bookmaker_A'], -opp['stake_A'])
                    bm.update(opp['bookmaker_B'], -opp['stake_B'])
                    
                    # Alerta Telegram
                    send_surebet_alert(opp)
                    surebet.alert_sent = True
                    new_bets += 1
            
            db.session.commit()
            logger.info(
                f"[Odds] Fonte={source} | {len(initial_opportunities)} oportunidades detectadas | "
                f"{len(confirmed_opportunities)} confirmadas | "
                f"{new_bets} novas surebets"
            )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"[Odds] FALHOU: {e}")


def _check_results_task(app):
    """Verifica resultados e liquida apostas pendentes."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.football_data import FootballDataClient
            from app.models import Game, Surebet
            from app import db
            from app.engine.bankroll_manager import BankrollManager
            
            bm = BankrollManager()
            fd_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
            if not fd_key:
                logger.error("[Results] FOOTBALL_DATA_API_KEY não configurada")
                return
            
            client = FootballDataClient(fd_key)
            recent = client.get_recent_results()
            if not recent:
                logger.error("[Results] API não retornou resultados recentes")
                return

            updated_games = 0
            settled_surebets = 0
            
            for result in recent:
                game = Game.query.filter_by(
                    home_team=result['home_team'],
                    away_team=result['away_team']
                ).filter(
                    Game.status != 'finished'
                ).first()
                
                if not game:
                    continue
                
                # Atualizar resultado
                game.home_score = result['home_score']
                game.away_score = result['away_score']
                game.status = 'finished'
                updated_games += 1
                
                # Liquidar Surebets (Arbitragem)
                pending_surebets = Surebet.query.filter_by(
                    game_id=game.id, status='pending'
                ).all()
                
                for s in pending_surebets:
                    s.status = 'settled'
                    # Adicionar retorno à banca (simplificado: retorno garantido)
                    # Na prática, o retorno vai para a casa onde a aposta venceu.
                    # Como o lucro é garantido em qualquer cenário, somamos stake + lucro.
                    total_return = s.total_stake + s.guaranteed_profit
                    # Aqui apenas simulamos a volta do dinheiro para manter o fluxo
                    bm.update(s.bookmaker_A, s.stake_A + (s.guaranteed_profit/2))
                    bm.update(s.bookmaker_B, s.stake_B + (s.guaranteed_profit/2))
                    settled_surebets += 1

            db.session.commit()
            logger.info(f"[Results] {updated_games} partidas atualizadas")
            if settled_surebets:
                logger.info(f"[Results] {settled_surebets} surebets liquidadas")
        except Exception as e:
            logger.error(f"[Results] FALHOU: {e}")


def _daily_retrain_task(app):
    """Retraining diário."""
    with app.app_context():
        try:
            from app.data.football_data import FootballDataClient
            from app.engine.ensemble import _get_global_ensemble, _set_global_ensemble

            ensemble = _get_global_ensemble()
            if not ensemble:
                logger.warning("[Retrain] Ensemble não carregado")
                return

            client = FootballDataClient(app.config.get('FOOTBALL_DATA_API_KEY', ''))
            df = client.get_historical_matches_df()

            if df is not None and len(df) >= 100:
                ensemble.train(df)
                ensemble.save()
                _set_global_ensemble(ensemble)
                logger.info(f"[Retrain] OK - {len(df)} jogos")
            else:
                logger.warning("[Retrain] Dados insuficientes")
        except Exception as e:
            logger.error(f"[Retrain] Erro: {e}")


def _daily_summary_task(app):
    """Resumo diário."""
    with app.app_context():
        try:
            from app.models import Bet
            from app.alerts.telegram_bot import send_message

            today = date.today()
            bets = Bet.query.filter(
                Bet.timestamp >= datetime.combine(today, datetime.min.time())
            ).all()
            wins = [b for b in bets if b.result == 'won']
            losses = [b for b in bets if b.result == 'lost']
            pnl = sum((b.profit_loss or 0.0) for b in bets)
            delivered = send_message(
                f"📋 <b>Resumo Diário - EdgeHunter</b>\n\n"
                f"📅 {today.strftime('%d/%m/%Y')}\n"
                f"🎯 Surebets: {len(bets)}\n"
                f"✅ Ganhos: {len(wins)}\n"
                f"❌ Perdas: {len(losses)}\n"
                f"💰 P&amp;L: R$ {pnl:.2f}"
            )

            if not delivered:
                logger.error("[Summary] Erro: Telegram não respondeu")
        except Exception as e:
            logger.error(f"[Summary] Erro: {e}")


def _update_metrics_task(app):
    """Atualizar métricas."""
    with app.app_context():
        try:
            from app import db
            from app.models import Game, Prediction
            from app.engine.ensemble import _get_global_ensemble

            cutoff = datetime.utcnow() - timedelta(days=30)
            preds = (
                db.session.query(Prediction, Game)
                .join(Game, Prediction.game_id == Game.id)
                .filter(Game.status == 'finished')
                .filter(Prediction.created_at >= cutoff)
                .all()
            )

            if len(preds) < 10:
                logger.info("[Metrics] Aguardando mais dados")
                return

            model_brier = {}
            model_columns = {
                'dixon_coles': ('dixon_coles_home', 'dixon_coles_draw', 'dixon_coles_away'),
                'elo': ('elo_home', 'elo_draw', 'elo_away'),
                'xgboost': ('xgboost_home', 'xgboost_draw', 'xgboost_away'),
                'bayesian': ('bayesian_home', 'bayesian_draw', 'bayesian_away'),
            }

            for model_name, columns in model_columns.items():
                scores = []
                for pred, game in preds:
                    hs, as_ = game.home_score, game.away_score
                    if hs is None or as_ is None:
                        continue

                    true = (1, 0, 0) if hs > as_ else ((0, 1, 0) if hs == as_ else (0, 0, 1))
                    probs = [getattr(pred, col, None) for col in columns]
                    if any(p is None for p in probs):
                        continue

                    bs = sum((float(probs[i]) - true[i]) ** 2 for i in range(3)) / 3
                    scores.append(bs)

                if scores:
                    model_brier[model_name] = float(np.mean(scores))

            if model_brier:
                ensemble = _get_global_ensemble()
                if ensemble:
                    ensemble.ensemble.update_weights_from_brier(model_brier)
                    logger.info(f"[Metrics] Brier: {json.dumps(model_brier, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"[Metrics] Erro: {e}")


def _heartbeat_task(app):
    with app.app_context():
        try:
            from app.alerts.telegram_bot import send_heartbeat
            from app.engine.gemini_engine import get_ai_engine
            from app.models import Surebet
            from datetime import datetime, date

            ai = get_ai_engine()

            surebets_today = Surebet.query.filter(
                Surebet.created_at >= datetime.combine(date.today(), datetime.min.time())
            ).count()

            scheduler = get_scheduler()
            jobs = scheduler.get_jobs()

            result = send_heartbeat(
                scheduler_jobs=jobs,
                ai_active=ai is not None,
                surebets_today=surebets_today
            )

            if result:
                logger.info("💓 Heartbeat enviado")
            else:
                logger.error("💓 Heartbeat FALHOU")
        except Exception as e:
            logger.error(f"💓 Heartbeat erro: {e}")


def _autotuner_task(app):
    with app.app_context():
        try:
            from app.engine.autotuner import AutoTuner

            tuner = AutoTuner()
            tuner.run_cycle()
            logger.info("[AutoTuner] Ciclo executado")
        except Exception as e:
            logger.error(f"[AutoTuner] Erro: {e}")
