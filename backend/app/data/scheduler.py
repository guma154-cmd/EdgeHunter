"""
EdgeHunter — Scheduler de tarefas automáticas
APScheduler gerencia todas as tarefas periódicas do sistema.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import pytz
from datetime import datetime, date

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
    
    # Heartbeat a cada 2 horas
    scheduler.add_job(
        func=lambda: _heartbeat_task(app),
        trigger=IntervalTrigger(hours=2),
        id='heartbeat',
        name='Heartbeat Telegram',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler iniciado com todas as tarefas")
    
    # Envio imediato do primeiro heartbeat
    try:
        _heartbeat_task(app)
    except Exception as e:
        logger.error(f"Erro no heartbeat inicial: {e}")
        
    return scheduler


def _fetch_odds_task(app):
    """Busca novas odds e detecta value bets."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.odds_api import OddsAPIClient
            from app.data.apifootball_client import APIFootballClient
            from app.data.oddsapiio_client import OddsApiIoClient
            from app.data.oddsportal_scraper import fetch_games_sync
            from app.models import Game, Bet, Surebet, SurebetStat
            from app import db
            from app.alerts.telegram_bot import TelegramBot, send_surebet_alert
            from app.detection.surebet_detector import SurebetDetector
            
            api_key = current_app.config['ODDS_API_KEY']
            apif_key = current_app.config.get('APIFOOTBALL_KEY')
            oddsio_key = current_app.config.get('ODDSAPIIO_KEY')
            
            games = []
            
            # 1. OddsPortal Scraper (Principal — Sem limites)
            try:
                logger.info("Iniciando OddsPortal Scraper (Fonte Primária)...")
                games = fetch_games_sync()
                if games:
                    logger.info(f"OddsPortal: {len(games)} jogos coletados com sucesso.")
            except Exception as e:
                logger.error(f"Erro no OddsPortal Scraper: {e}")

            # 2. Odds-api.io (Fallback 1)
            if not games and oddsio_key:
                try:
                    logger.info("OddsPortal falhou ou sem jogos → Fallback para Odds-API.io...")
                    oddsio_client = OddsApiIoClient(oddsio_key)
                    games = oddsio_client.fetch_games_with_odds()
                except Exception as e:
                    logger.error(f"Erro no Odds-API.io: {e}")

            # 3. The Odds API (Fallback 2)
            if not games and api_key:
                try:
                    logger.info("The Odds API Fallback...")
                    client = OddsAPIClient(api_key)
                    games = client.fetch_all_value_games()
                except Exception as e:
                    logger.error(f"Erro na Odds API: {e}")

            # 3. API-Football (Fallback)
            if not games and apif_key:
                try:
                    logger.info("API-Football Direct Fallback...")
                    apif_client = APIFootballClient(apif_key)
                    games = apif_client.fetch_odds()
                except Exception as e:
                    logger.error(f"Erro na API-Football: {e}")
            
            if not games:
                logger.warning("Nenhum jogo retornado. Todas as APIs indisponíveis.")
                return
            
            # Carregar ensemble global (opcional para Surebets)
            from app.engine.ensemble import _get_global_ensemble
            ensemble = _get_global_ensemble()
            ensemble_ready = ensemble is not None and ensemble.is_ready
            
            if not ensemble_ready:
                logger.info("Ensemble não pronto. Prosseguindo apenas com Surebets.")
            
            detector = SurebetDetector(
                min_profit_pct=current_app.config.get('MIN_SUREBET_PROFIT', 1.0)
            )
            
            telegram = TelegramBot(
                current_app.config['TELEGRAM_BOT_TOKEN'],
                current_app.config['TELEGRAM_CHAT_ID']
            )
            
            new_bets = 0
            
            for game_data in games:
                # Checar ou criar jogo no banco
                game = Game.query.filter_by(
                    home_team=game_data['home_team'],
                    away_team=game_data['away_team'],
                    league=game_data['league']
                ).first()
                
                if not game:
                    game = Game(
                        home_team=game_data['home_team'],
                        away_team=game_data['away_team'],
                        league=game_data['league'],
                        match_date=datetime.fromisoformat(game_data['match_date'].replace('Z', '+00:00')),
                        status='scheduled'
                    )
                    db.session.add(game)
                    db.session.flush()
                
                # Detecção de Surebet
                opportunities = detector.detect(game_data)
                
                for opp in opportunities:
                    # Verificar se já existe essa surebet para este jogo/casas/profit
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
                        
                        # Auto-aprendizado
                        SurebetStat.update_stats(
                            opp['bookmaker_A'], 
                            opp['bookmaker_B'], 
                            game.league, 
                            opp['profit_pct']
                        )
                        
                        # Alerta Telegram
                        send_surebet_alert(opp)
                        surebet.alert_sent = True
                        new_bets += 1
            
            db.session.commit()
            logger.info(f"Surebet task: {len(games)} jogos analisados, {new_bets} novas arbitragens")
        
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
                    from app.models.game import Prediction
                    from app.models import Game
                
                    model_brier_scores = {}
                    sub_models = ['dixon_coles', 'elo', 'xgboost', 'bayesian']
                
                    for model_name in sub_models:
                        # Buscar predições com resultado conhecido
                        preds_with_results = db.session.query(
                            Prediction, Game
                        ).join(
                            Game, Prediction.game_id == Game.id
                        ).filter(
                            Game.status == 'finished',
                            Game.home_score.isnot(None),
                            Prediction.created_at >= cutoff
                        ).all()
                
                        if not preds_with_results:
                            continue
                
                        brier_scores = []
                        for pred, game in preds_with_results:
                            # Resultado real como vetor one-hot
                            if game.home_score > game.away_score:
                                true_vec = (1, 0, 0)
                            elif game.home_score == game.away_score:
                                true_vec = (0, 1, 0)
                            else:
                                true_vec = (0, 0, 1)
                
                            # Probabilidades do sub-modelo específico
                            if model_name == 'dixon_coles':
                                p = (pred.dixon_coles_home or 1/3,
                                     pred.dixon_coles_draw or 1/3,
                                     pred.dixon_coles_away or 1/3)
                            elif model_name == 'elo':
                                p = (pred.elo_home or 1/3,
                                     pred.elo_draw or 1/3,
                                     pred.elo_away or 1/3)
                            elif model_name == 'xgboost':
                                p = (pred.xgboost_home or 1/3,
                                     pred.xgboost_draw or 1/3,
                                     pred.xgboost_away or 1/3)
                            elif model_name == 'bayesian':
                                p = (pred.bayesian_home or 1/3,
                                     pred.bayesian_draw or 1/3,
                                     pred.bayesian_away or 1/3)
                
                            # Brier Score multiclasse
                            bs = sum((p[i] - true_vec[i])**2 for i in range(3)) / 3
                            brier_scores.append(bs)
                
                        if brier_scores:
                            model_brier_scores[model_name] = float(np.mean(brier_scores))
                            logger.info(
                                f"Brier Score real — {model_name}: "
                                f"{model_brier_scores[model_name]:.4f} "
                                f"({len(brier_scores)} amostras)"
                            )
                
                    if model_brier_scores:
                        ensemble.ensemble.update_weights_from_brier(model_brier_scores)
                        logger.info(f"Pesos reais atualizados: {model_brier_scores}")
            
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


def _heartbeat_task(app):
    with app.app_context():
        try:
            from app.alerts.telegram_bot import send_heartbeat
            from app.engine.ensemble import _get_global_ensemble
            from app.engine.gemini_engine import get_ai_engine
            from app.models import Bet
            from datetime import datetime, date

            ensemble = _get_global_ensemble()
            ai = get_ai_engine()

            surebets_today = Bet.query.filter(
                Bet.mode == 'paper',
                Bet.timestamp >= datetime.combine(date.today(), datetime.min.time())
            ).count()

            scheduler = get_scheduler()
            jobs = scheduler.get_jobs()

            send_heartbeat(
                scheduler_jobs=jobs,
                ai_active=ai is not None,
                surebets_today=surebets_today
            )
            logger.info("💓 Heartbeat enviado com sucesso!")
        except Exception as e:
            logger.error(f"Erro no heartbeat: {e}")
