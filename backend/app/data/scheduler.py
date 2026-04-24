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
            from app.alerts.telegram_bot import TelegramBot, send_surebet_alert
            from app.detection.surebet_detector import SurebetDetector
            from app.engine.bankroll_manager import BankrollManager
            
            bm = BankrollManager()
            games = fetch_games_sync()
            
            if not games:
                logger.warning("Nenhum jogo retornado pelo scraper.")
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
            logger.info(f"Surebet task: {len(confirmed_opportunities)} confirmadas de {len(initial_opportunities)} detectadas.")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Erro na tarefa de odds: {e}")


def _check_results_task(app):
    """Verifica resultados e liquida apostas pendentes."""
    with app.app_context():
        try:
            from flask import current_app
            from app.data.football_data import FootballDataClient
            from app.models import Game, Bet, Surebet
            from app import db
            from app.engine.bankroll_manager import BankrollManager
            
            bm = BankrollManager()
            fd_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
            if not fd_key:
                return
            
            client = FootballDataClient(fd_key)
            recent = client.get_recent_results()
            
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

            db.session.commit()
        except Exception as e:
            logger.error(f"Erro na tarefa de resultados: {e}")


def _retrain_task(app):
    """Retraining diário."""
    pass


def _daily_summary_task(app):
    """Resumo diário."""
    pass


def _update_metrics_task(app):
    """Atualizar métricas."""
    pass


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

            send_heartbeat(
                scheduler_jobs=jobs,
                ai_active=ai is not None,
                surebets_today=surebets_today
            )
            logger.info("💓 Heartbeat enviado com sucesso!")
        except Exception as e:
            logger.error(f"Erro no heartbeat: {e}")
