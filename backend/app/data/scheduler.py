"""
EdgeHunter — Scheduler de tarefas automáticas
APScheduler gerencia todas as tarefas periódicas do sistema.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
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


def _confirm_surebet_fast(opp: dict) -> bool:
    """
    Re-scrapa APENAS o jogo detectado de forma instantânea.
    Sem sleep — confirmação rápida para não perder a janela.
    """
    try:
        game_url = opp.get('source_url', '')
        if not game_url:
            return True
        
        import asyncio
        from playwright.async_api import async_playwright
        from app.data.oddsportal_scraper import OddsPortalScraper
        
        async def quick_check():
            scraper = OddsPortalScraper()
            async with async_playwright() as p:
                await scraper._init_browser(p)
                page = await scraper.context.new_page()
                game = await scraper._scrape_match_odds(
                    page, game_url,
                    opp['league'], opp['home_team'] + " vs " + opp['away_team']
                )
                await scraper.browser.close()
                return game
        
        game = asyncio.run(quick_check())
        if not game:
            return False
        
        # Verificar se a arbitragem ainda existe
        from app.detection.surebet_detector import SurebetDetector
        detector = SurebetDetector()
        new_opps = detector.detect(game)
        
        still_valid = any(
            o['bookmaker_A'] == opp['bookmaker_A'] and
            o['bookmaker_B'] == opp['bookmaker_B'] and
            abs(o['odds_A'] - opp['odds_A']) < 0.05
            for o in new_opps
        )
        return still_valid
    except Exception as e:
        logger.error(f"Erro na confirmação rápida: {e}")
        return True


def _fetch_odds_task(app):
    """Busca novas odds e detecta value bets."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.oddsportal_scraper import fetch_games_sync
            from app.models import Game, Surebet
            from app import db
            from app.alerts.telegram_bot import send_surebet_alert
            from app.detection.surebet_detector import SurebetDetector
            from app.engine.bankroll_manager import BankrollManager
            
            bm = BankrollManager()
            games = fetch_games_sync()
            
            if not games:
                logger.error("fetch_odds FALHOU: scraper retornou 0 jogos.")
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
                logger.info(f"fetch_odds OK: {len(games)} jogos coletados | 0 oportunidades detectadas.")
                return

            # CONFIRMAÇÃO RÁPIDA E FILTRO DE BANCA
            confirmed_opportunities = []
            for opp in initial_opportunities:
                # 1. Verificar se tem banca para cobrir
                if not bm.can_cover(opp['bookmaker_A'], opp['stake_A'], 
                                   opp['bookmaker_B'], opp['stake_B']):
                    logger.info(f"Surebet ignorada por falta de banca: {opp['bookmaker_A']}/{opp['bookmaker_B']}")
                    continue
                
                # 2. Re-scrape instantâneo para confirmar odd
                if _confirm_surebet_fast(opp):
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
                "fetch_odds OK: "
                f"{len(games)} jogos coletados | "
                f"{len(initial_opportunities)} oportunidades detectadas | "
                f"{len(confirmed_opportunities)} confirmadas | "
                f"{new_bets} novas surebets."
            )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"fetch_odds FALHOU: {e}")


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
                logger.error("check_results FALHOU: FOOTBALL_DATA_API_KEY não configurada.")
                return
            
            client = FootballDataClient(fd_key)
            recent = client.get_recent_results()
            if not recent:
                logger.error("check_results FALHOU: API não retornou resultados recentes.")
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
            logger.info(
                "check_results OK: "
                f"{updated_games} jogos atualizados | "
                f"{settled_surebets} surebets liquidadas."
            )
        except Exception as e:
            logger.error(f"check_results FALHOU: {e}")


def _retrain_task(app):
    """Retraining diário."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.football_data import FootballDataClient
            from app.engine.ensemble import _get_global_ensemble, _set_global_ensemble

            ensemble = _get_global_ensemble()
            if ensemble is None:
                logger.error("daily_retrain FALHOU: ensemble global não carregado.")
                return

            fd_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
            if not fd_key:
                logger.error("daily_retrain FALHOU: FOOTBALL_DATA_API_KEY não configurada.")
                return

            client = FootballDataClient(fd_key)
            df = client.get_historical_matches_df()

            if df is None or len(df) <= 100:
                logger.warning("Retraining: dados insuficientes")
                return

            ensemble.train(df)
            ensemble.save()
            _set_global_ensemble(ensemble)
            logger.info(f"Retraining OK: {len(df)} jogos")
        except Exception as e:
            logger.error(f"daily_retrain FALHOU: {e}")


def _daily_summary_task(app):
    """Resumo diário."""
    with app.app_context():
        try:
            from app.models import Bet
            from app.alerts.telegram_bot import send_message

            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            bets = Bet.query.filter(Bet.timestamp >= today_start).all()
            wins = [bet for bet in bets if bet.result == 'won']
            losses = [bet for bet in bets if bet.result == 'lost']
            pnl = sum((bet.profit_loss or 0.0) for bet in bets)

            delivered = send_message(
                f"📋 <b>Resumo Diário — EdgeHunter</b>\n\n"
                f"📅 {today.strftime('%d/%m/%Y')}\n"
                f"🎯 Surebets: {len(bets)}\n"
                f"✅ Ganhos: {len(wins)}\n"
                f"❌ Perdas: {len(losses)}\n"
                f"💰 P&amp;L: R$ {pnl:.2f}\n"
            )

            if delivered:
                logger.info(
                    f"daily_summary OK: {len(bets)} apostas | "
                    f"{len(wins)} ganhos | {len(losses)} perdas | "
                    f"P&L R$ {pnl:.2f}."
                )
            else:
                logger.error("daily_summary FALHOU: Telegram não respondeu.")
        except Exception as e:
            logger.error(f"daily_summary FALHOU: {e}")


def _update_metrics_task(app):
    """Atualizar métricas."""
    with app.app_context():
        try:
            from flask import current_app
            from app import db
            from app.engine.calibration import brier_score
            from app.models import Bet, Game, ModelVersion, Performance, Prediction

            completed_predictions = (
                Prediction.query
                .join(Game, Prediction.game_id == Game.id)
                .filter(
                    Game.status == 'finished',
                    Game.home_score.isnot(None),
                    Game.away_score.isnot(None)
                )
                .all()
            )

            if len(completed_predictions) < 10:
                logger.info("Métricas: aguardando dados")
                return

            prediction_scores = []
            scores_by_model = {}
            updated_predictions = 0

            for prediction in completed_predictions:
                game = prediction.game
                actual = np.array([
                    1.0 if game.home_score > game.away_score else 0.0,
                    1.0 if game.home_score == game.away_score else 0.0,
                    1.0 if game.home_score < game.away_score else 0.0,
                ])
                probs = np.array([
                    prediction.prob_home,
                    prediction.prob_draw,
                    prediction.prob_away,
                ])

                score = (
                    brier_score(actual[[0]], probs[[0]]) +
                    brier_score(actual[[1]], probs[[1]]) +
                    brier_score(actual[[2]], probs[[2]])
                ) / 3

                if prediction.brier_score != score:
                    prediction.brier_score = score
                    updated_predictions += 1

                prediction_scores.append(score)
                if prediction.model_version_id:
                    scores_by_model.setdefault(prediction.model_version_id, []).append(score)

            active_model = ModelVersion.query.filter_by(is_active=True).first()
            if active_model is None:
                db.session.commit()
                logger.info(
                    f"update_metrics OK: {len(prediction_scores)} predições avaliadas | "
                    f"Brier médio {float(np.mean(prediction_scores)):.4f} | "
                    "sem modelo ativo para persistir métricas agregadas."
                )
                return

            today = date.today()
            rolling_window_days = current_app.config.get('ROLLING_WINDOW_DAYS', 30)
            rolling_cutoff = datetime.utcnow() - timedelta(days=rolling_window_days)

            settled_bets = Bet.query.filter(
                Bet.timestamp >= datetime.combine(today, datetime.min.time()),
                Bet.result.in_(['won', 'lost'])
            ).all()
            rolling_bets = Bet.query.filter(
                Bet.timestamp >= rolling_cutoff,
                Bet.result.in_(['won', 'lost'])
            ).all()

            profits_today = [bet.profit_loss for bet in settled_bets if bet.profit_loss is not None]
            stakes_today = [bet.stake for bet in settled_bets]
            clv_today = [bet.clv for bet in settled_bets if bet.clv is not None]

            rolling_rois = [bet.roi for bet in rolling_bets if bet.roi is not None]
            rolling_profits = [bet.profit_loss for bet in rolling_bets if bet.profit_loss is not None]
            rolling_clv = [bet.clv for bet in rolling_bets if bet.clv is not None]
            rolling_stake = sum(bet.stake for bet in rolling_bets)

            roi_today = (sum(profits_today) / sum(stakes_today) * 100) if stakes_today else 0.0
            roi_30d = (sum(rolling_profits) / rolling_stake * 100) if rolling_stake > 0 else 0.0
            sharpe_30d = 0.0
            if len(rolling_rois) > 1 and np.std(rolling_rois) > 0:
                sharpe_30d = float(np.mean(rolling_rois) / np.std(rolling_rois))

            active_brier_scores = scores_by_model.get(active_model.id, prediction_scores)
            active_brier = float(np.mean(active_brier_scores)) if active_brier_scores else None
            clv_avg_30d = float(np.mean(rolling_clv)) if rolling_clv else 0.0

            active_model.brier_score = active_brier
            active_model.roi_30d = roi_30d
            active_model.clv_avg = clv_avg_30d
            active_model.sharpe_ratio = sharpe_30d
            active_model.total_bets = len(rolling_bets)

            daily_perf = Performance.query.filter_by(
                model_version_id=active_model.id,
                date=today
            ).first()
            if daily_perf is None:
                daily_perf = Performance(model_version_id=active_model.id, date=today)
                db.session.add(daily_perf)

            daily_perf.bets_count = len(settled_bets)
            daily_perf.wins = sum(1 for bet in settled_bets if bet.result == 'won')
            daily_perf.losses = sum(1 for bet in settled_bets if bet.result == 'lost')
            daily_perf.profit_loss = float(sum(profits_today)) if profits_today else 0.0
            daily_perf.roi = float(roi_today)
            daily_perf.brier_score = active_brier
            daily_perf.clv_avg = float(np.mean(clv_today)) if clv_today else 0.0
            daily_perf.sharpe_30d = sharpe_30d
            daily_perf.roi_30d = roi_30d

            db.session.commit()
            logger.info(
                "update_metrics OK: "
                f"{len(prediction_scores)} predições avaliadas | "
                f"{updated_predictions} atualizadas | "
                f"Brier médio {float(np.mean(prediction_scores)):.4f} | "
                f"ROI {rolling_window_days}d {roi_30d:+.2f}%."
            )
        except Exception as e:
            logger.error(f"update_metrics FALHOU: {e}")


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
                logger.info("💓 Heartbeat enviado com sucesso!")
            else:
                logger.error("💓 Heartbeat FALHOU: Telegram não respondeu")
        except Exception as e:
            logger.error(f"💓 Heartbeat erro: {e}")
