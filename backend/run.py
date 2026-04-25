"""
EdgeHunter Backend — Entry Point
"""
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s — %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

from app import create_app, db
from app.data.scheduler import get_scheduler, start_scheduler

# Timestamp de deploy: 2026-04-25 11:25
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("[OK] Database inicializado")
        
        from app.engine.ensemble import ModelEnsemble, _set_global_ensemble
        
        # Carregar ensemble do disco ou alertar para treinar do zero
        if os.path.exists('models/ensemble_state.joblib'):
            try:
                ensemble = ModelEnsemble.load()
                _set_global_ensemble(ensemble)
                print('[OK] Ensemble carregado do disco')
            except Exception as e:
                print(f'[ERRO] Falha ao carregar ensemble: {e}')
                print('[WARN] Execute: python seed_historical.py')
        else:
            print('[WARN] Ensemble não encontrado')
            print('[WARN] Execute: python seed_historical.py')

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser_path = p.chromium.executable_path
            if browser_path and os.path.exists(browser_path):
                print('[OK] Playwright browser disponível')
            else:
                print('[WARN] Playwright browser não encontrado')
        except Exception as e:
            print(f'[WARN] Playwright browser indisponível: {e}')

        if app.config.get('BOLTODDS_API_KEY'):
            print('[OK] BoltOdds configurado')
        else:
            print('[WARN] BoltOdds não configurado')

        # Telegram startup (Mover para dentro do contexto)
        try:
            from app.alerts.telegram_bot import TelegramBot, send_startup_message
            bot = TelegramBot(
                app.config['TELEGRAM_BOT_TOKEN'],
                app.config['TELEGRAM_CHAT_ID']
            )
            bot.test_connection()
            send_startup_message()
            print("[OK] Telegram conectado")
        except Exception as e:
            print(f"[WARN] Telegram startup falhou: {e}")

    start_scheduler(app)
    print(f"[OK] Scheduler: {len(get_scheduler().get_jobs())} jobs ativos")
    print("[OK] AutoTuner registrado")

    # Motor hibrido startup
    from app.engine.gemini_engine import init_ai_engine
    gemini_key = app.config.get('GEMINI_API_KEY', '')
    groq_key   = app.config.get('GROQ_API_KEY', '')
    if gemini_key and groq_key:
        init_ai_engine(gemini_key, groq_key)
        print("[OK] Motor IA hibrido ativo: Gemini 2.5 Flash + Groq Llama 3.3 70B")
    else:
        print("[WARN] Chaves de IA nao configuradas — rodando sem filtro de IA")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False),
        use_reloader=False
    )
