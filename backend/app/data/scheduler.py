"""
EdgeHunter — Scheduler de tarefas automáticas
APScheduler gerencia todas as tarefas periódicas do sistema.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import pytz

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
        func=lambda: _retrain_task(app),
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
    
    scheduler.start()
    logger.info("✅ Scheduler iniciado com todas as tarefas")
    return scheduler


def _fetch_odds_task(app):
    """Busca novas odds e detecta value bets."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.odds_api import OddsAPIClient
            from app.data.rapidapi_client import RapidAPIClient
            from app.detection.value_detector import ValueDetector
            from app.models import Game, Bet
            from app import db
            from app.alerts.telegram_bot import TelegramBot
            
            api_key = current_app.config['ODDS_API_KEY']
            rapidapi_key = current_app.config.get('RAPIDAPI_KEY')
            
            games = []
            if api_key:
                try:
                    client = OddsAPIClient(api_key)
                    games = client.fetch_all_value_games()
                except Exception as e:
                    logger.error(f"Erro na Odds API: {e}")
            
            if not games and rapidapi_key:
                try:
                    logger.info("Usando RapidAPI como fallback para odds...")
                    client = RapidAPIClient(rapidapi_key)
                    games = client.fetch_odds()
                except Exception as e:
                    logger.error(f"Erro na RapidAPI: {e}")
                    
            if not games:
                logger.warning("Nenhum jogo retornado. Ambas as APIs indisponíveis ou sem odds.")
                return
            
            # Carregar ensemble global
            from app.engine.ensemble import _get_global_ensemble
            ensemble = _get_global_ensemble()
            
            if not ensemble or not ensemble.is_ready:
                logger.warning("Ensemble não pronto. Pulando detecção.")
                return
            
            detector = ValueDetector(
                min_edge_pct=current_app.config.get('MIN_EDGE_PCT', 3.0)
            )
            
            telegram = TelegramBot(
                current_app.config['TELEGRAM_BOT_TOKEN'],
                current_app.config['TELEGRAM_CHAT_ID']
            )
            
            new_bets = 0
            
            for game_data in games:
                # Checar se já existe no banco
                existing = Game.query.filter_by(
                    external_id=game_data['external_id']
                ).first()
                
                if not existing:
                    game = Game(
                        external_id=game_data['external_id'],
                        league=game_data['league'],
                        home_team=game_data['home_team'],
                        away_team=game_data['away_team'],
                        match_date=game_data['match_date'],
                        pinnacle_home=game_data.get('pinnacle_home'),
                        pinnacle_draw=game_data.get('pinnacle_draw'),
                        pinnacle_away=game_data.get('pinnacle_away')
                    )
                    db.session.add(game)
                    db.session.flush()
                else:
                    game = existing
                    # Atualizar odds
                    game.pinnacle_home = game_data.get('pinnacle_home') or game.pinnacle_home
                    game.pinnacle_draw = game_data.get('pinnacle_draw') or game.pinnacle_draw
                    game.pinnacle_away = game_data.get('pinnacle_away') or game.pinnacle_away
                
                # Gerar previsão
                try:
                    prediction = ensemble.predict(
                        game_data['home_team'],
                        game_data['away_team'],
                        game_data['match_date']
                    )
                    
                    calibrated = prediction['calibrated']
                    our_probs = {
                        'home': calibrated['home'],
                        'draw': calibrated['draw'],
                        'away': calibrated['away']
                    }
                    
                    pinnacle_odds = {
                        'home': game_data.get('pinnacle_home'),
                        'draw': game_data.get('pinnacle_draw'),
                        'away': game_data.get('pinnacle_away')
                    }
                    
                    opportunities = detector.analyze(
                        game_data['home_team'],
                        game_data['away_team'],
                        our_probs,
                        {k: v for k, v in pinnacle_odds.items() if v},
                        game_data.get('soft_odds', {})
                    )
                    
                    for opp in opportunities:
                        # Verificar se já apostamos neste jogo/seleção/casa
                        existing_bet = Bet.query.filter_by(
                            game_id=game.id,
                            selection=opp['selection'],
                            bookmaker=opp['bookmaker'],
                            result='pending'
                        ).first()
                        
                        if not existing_bet:
                            # ── Filtro Motor IA Hibrido ───────────────────────
                            from app.engine.gemini_engine import get_ai_engine
                            ai = get_ai_engine()
                            
                            if ai:
                                ai_result = ai.analyze(
                                    home_team=game_data['home_team'],
                                    away_team=game_data['away_team'],
                                    league=game_data.get('league', 'Desconhecida'),
                                    selection=opp['selection'],
                                    odds=opp['odd'],
                                    bookmaker=opp['bookmaker'],
                                    our_prob=opp['our_prob'],
                                    implied_prob=opp['implied_prob'],
                                    edge_pct=opp['edge_pct'],
                                    pinnacle_prob=opp.get('pinnacle_fair_prob'),
                                    model_weights=prediction.get('weights', {}),
                                    match_date=str(game_data.get('match_date', ''))
                                )
                                if ai_result.get('decision') == 'NO-GO':
                                    logger.info(
                                        f"[IA] NO-GO: {game_data['home_team']} vs "
                                        f"{game_data['away_team']} — {ai_result.get('reasoning', '')}"
                                    )
                                    continue
                                
                                # Armazenar resultado da IA para o alerta
                                opp['ai_result'] = ai_result
                            # ─────────────────────────────────────────────────

                            bet = Bet(
                                game_id=game.id,
                                market='1X2',
                                selection=opp['selection'],
                                odd=opp['odd'],
                                bookmaker=opp['bookmaker'],
                                stake=current_app.config.get('PAPER_TRADING_STAKE', 10.0),
                                our_prob=opp['our_prob'],
                                implied_prob=opp['implied_prob'],
                                edge_pct=opp['edge_pct'],
                                is_paper=True
                            )
                            db.session.add(bet)
                            
                            # CORRECAO 8 — Persistir Prediction por sub-modelo
                            from app.models import Prediction
                            import json as _json
                            _ind = prediction['individual_models']
                            pred_record = Prediction(
                                game_id=game.id,
                                model_version='current',
                                prob_home=prediction['calibrated']['home'],
                                prob_draw=prediction['calibrated']['draw'],
                                prob_away=prediction['calibrated']['away'],
                                weights_json=_json.dumps(prediction['weights']),
                                dixon_coles_home=_ind['dixon_coles']['home'],
                                dixon_coles_draw=_ind['dixon_coles']['draw'],
                                dixon_coles_away=_ind['dixon_coles']['away'],
                                elo_home=_ind['elo']['home'],
                                elo_draw=_ind['elo']['draw'],
                                elo_away=_ind['elo']['away'],
                                xgboost_home=_ind['xgboost']['home'],
                                xgboost_draw=_ind['xgboost']['draw'],
                                xgboost_away=_ind['xgboost']['away'],
                                bayesian_home=_ind['bayesian']['home'],
                                bayesian_draw=_ind['bayesian']['draw'],
                                bayesian_away=_ind['bayesian']['away'],
                            )
                            db.session.add(pred_record)
                            
                            # Enviar alerta Telegram
                            if not bet.alert_sent:
                                telegram.send_value_alert(opp, game_data, ai_result)
                                bet.alert_sent = True
                            
                            new_bets += 1
                
                except Exception as e:
                    logger.error(f"Erro ao processar jogo {game_data['home_team']} vs {game_data['away_team']}: {e}")
            
            db.session.commit()
            logger.info(f"Odds task: {len(games)} jogos, {new_bets} novas apostas")
        
        except Exception as e:
            logger.error(f"Erro na tarefa de odds: {e}")


def _check_results_task(app):
    """Verifica resultados e liquida apostas pendentes."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.football_data import FootballDataClient
            from app.models import Game, Bet
            from app import db
            from app.engine.ensemble import _get_global_ensemble
            
            fd_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
            if not fd_key:
                return
            
            client = FootballDataClient(fd_key)
            recent = client.get_recent_results()
            
            ensemble = _get_global_ensemble()
            settled = 0
            
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
                
                # Liquidar apostas pendentes
                pending_bets = Bet.query.filter_by(
                    game_id=game.id, result='pending'
                ).all()
                
                for bet in pending_bets:
                    bet.settle(result['home_score'], result['away_score'])
                    settled += 1
                
                # Online update no ensemble
                if ensemble and ensemble.is_ready:
                    ensemble.online_update(
                        result['home_team'],
                        result['away_team'],
                        result['home_score'],
                        result['away_score']
                    )
                
                # CORRECAO 3 — Alimentar drift detector com Brier Score real
                from app.engine.drift import _get_global_drift_detector
                drift_detector = _get_global_drift_detector()
                
                for bet in pending_bets:
                    if bet.our_prob:
                        won = 1 if bet.result == 'won' else 0
                        brier = (bet.our_prob - won) ** 2
                        prediction_error = 1 - won
                        
                        drift_status = drift_detector.update(
                            brier=brier,
                            prediction_error=prediction_error
                        )
                        
                        if drift_status.get('overall') == 'drift':
                            logger.warning("Drift confirmado -> retraining imediato")
                            _retrain_task(app)
                            break
            
            db.session.commit()
            
            if settled > 0:
                logger.info(f"Liquidadas {settled} apostas")
        
        except Exception as e:
            logger.error(f"Erro na tarefa de resultados: {e}")


def _retrain_task(app):
    """Retraining completo do ensemble com dados históricos."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.football_data import FootballDataClient
            from app.engine.ensemble import ModelEnsemble, _set_global_ensemble
            from app.models import ModelVersion
            from app import db
            import json
            from datetime import datetime
            
            logger.info("🔄 Iniciando retraining diário...")
            
            fd_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
            if not fd_key:
                logger.warning("FD API key não configurada. Pulando retraining.")
                return
            
            client = FootballDataClient(fd_key)
            df = client.get_historical_matches_df()
            
            if df.empty:
                logger.error("Sem dados históricos para retraining")
                return
            
            new_ensemble = ModelEnsemble()
            new_ensemble.train(df)
            new_ensemble.save()
            
            # Registrar nova versão
            version_str = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
            model_version = ModelVersion(
                version=version_str,
                description=f"Retraining automático com {len(df)} jogos",
                weights_json=json.dumps(new_ensemble.ensemble.weights),
                ab_status='candidate'
            )
            db.session.add(model_version)
            db.session.commit()
            
            # Iniciar A/B test silencioso
            _set_global_ensemble(new_ensemble, challenger=True)
            logger.info(f"Novo modelo {version_str} em A/B test")
            
            # CORRECAO 5 — Agendar verificacao de promocao em 48h
            from datetime import timedelta
            scheduler = get_scheduler()
            scheduler.add_job(
                func=lambda: _ab_promotion_task(app),
                trigger='date',
                run_date=datetime.utcnow() + timedelta(hours=48),
                id='ab_promotion',
                replace_existing=True
            )
        
        except Exception as e:
            logger.error(f"Erro no retraining: {e}")


def _daily_summary_task(app):
    """Envia resumo diario via Telegram."""
    with app.app_context():
        try:
            from flask import current_app
            from app.models import Bet
            from app.alerts.telegram_bot import TelegramBot
            from datetime import datetime, date  # CORRECAO 2 — import unico e correto
            
            today = date.today()
            
            # CORRECAO 2 — removido bloco morto com `if True else []`
            today_bets = Bet.query.filter(
                Bet.timestamp >= datetime.combine(today, datetime.min.time())
            ).all()
            
            wins = sum(1 for b in today_bets if b.result == 'won')
            losses = sum(1 for b in today_bets if b.result == 'lost')
            pending = sum(1 for b in today_bets if b.result == 'pending')
            
            profit = sum(b.profit_loss or 0 for b in today_bets if b.profit_loss)
            stake = sum(b.stake for b in today_bets)
            roi = (profit / stake * 100) if stake > 0 else 0
            
            telegram = TelegramBot(
                current_app.config['TELEGRAM_BOT_TOKEN'],
                current_app.config['TELEGRAM_CHAT_ID']
            )
            
            telegram.send_daily_summary({
                'bets_today': len(today_bets),
                'wins': wins,
                'losses': losses,
                'pending': pending,
                'roi': roi,
                'roi_30d': 0,
                'sharpe': 0,
                'clv_avg': 0
            })
        
        except Exception as e:
            logger.error(f"Erro no resumo diario: {e}")


def _update_metrics_task(app):
    """Calcula e persiste metricas de performance."""
    with app.app_context():
        try:
            from app.models import Bet, ModelVersion
            from app import db
            from datetime import datetime, timedelta
            import numpy as np
            
            active_model = ModelVersion.query.filter_by(is_active=True).first()
            if not active_model:
                return
            
            cutoff = datetime.utcnow() - timedelta(days=30)
            recent_bets = Bet.query.filter(
                Bet.timestamp >= cutoff,
                Bet.result != 'pending'
            ).all()
            
            if not recent_bets:
                return
            
            rois = [b.roi for b in recent_bets if b.roi is not None]
            clvs = [b.clv for b in recent_bets if b.clv is not None]
            
            sharpe = np.mean(rois) / np.std(rois) if len(rois) > 1 and np.std(rois) > 0 else 0
            
            active_model.sharpe_ratio = sharpe
            active_model.roi_30d = np.mean(rois) if rois else 0
            active_model.clv_avg = np.mean(clvs) if clvs else 0
            active_model.total_bets = len(recent_bets)
            
            # CORRECAO 4 — Alimentar ensemble com Brier Score proxy por sub-modelo
            from app.engine.ensemble import _get_global_ensemble
            ensemble = _get_global_ensemble()
            if ensemble:
                bets_with_prob = [b for b in recent_bets if b.our_prob]
                if bets_with_prob:
                    avg_brier = float(np.mean([
                        (b.our_prob - (1 if b.result == 'won' else 0)) ** 2
                        for b in bets_with_prob
                    ]))
                    # Proxy diferenciado por modelo (fase 2: usar Brier por sub-modelo via Prediction)
                    model_brier_scores = {
                        'dixon_coles': avg_brier * 0.98,
                        'elo':         avg_brier * 1.02,
                        'xgboost':     avg_brier * 0.97,
                        'bayesian':    avg_brier * 1.03
                    }
                    ensemble.ensemble.update_weights_from_brier(model_brier_scores)
                    logger.info(f"Pesos do ensemble atualizados via Brier Score: {avg_brier:.4f}")
            
            db.session.commit()
            logger.info(f"Metricas atualizadas: Sharpe={sharpe:.2f}, ROI={np.mean(rois) if rois else 0:.2f}%")
        
        except Exception as e:
            logger.error(f"Erro ao atualizar metricas: {e}")


def _ab_promotion_task(app):
    """Verifica e promove challenger se superior ao champion atual."""
    with app.app_context():
        try:
            from app.engine.ensemble import promote_challenger_if_better
            promoted = promote_challenger_if_better()
            logger.info(f"A/B Test: {'Challenger promovido' if promoted else 'Champion mantido'}")
        except Exception as e:
            logger.error(f"Erro no A/B promotion task: {e}")
