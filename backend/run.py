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
from app.data.scheduler import start_scheduler

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("[OK] Database inicializado")
        
        from app.engine.ensemble import ModelEnsemble, _set_global_ensemble
        import os
        
        # Carregar ensemble do disco ou alertar para treinar do zero
        if ModelEnsemble.exists():
            try:
                ensemble = ModelEnsemble.load()
                _set_global_ensemble(ensemble)
                print('[OK] Ensemble carregado do disco')
            except Exception as e:
                print(f'[WARN] Falha ao carregar ensemble: {e}')
                print('[INFO] Execute seed_historical.py para treinar')
        else:
            print('[WARN] Ensemble nao encontrado — execute seed_historical.py')

    start_scheduler(app)
    print("[OK] Scheduler iniciado")

    # Motor hibrido startup
    from app.engine.gemini_engine import init_ai_engine
    gemini_key = app.config.get('GEMINI_API_KEY', '')
    groq_key   = app.config.get('GROQ_API_KEY', '')
    if gemini_key and groq_key:
        init_ai_engine(gemini_key, groq_key)
        print("[OK] Motor IA hibrido ativo: Gemini 2.5 Flash + Groq Llama 3.3 70B")
    else:
        print("[WARN] Chaves de IA nao configuradas — rodando sem filtro de IA")

    # Telegram startup
    try:
        from app.alerts.telegram_bot import TelegramBot
        bot = TelegramBot(
            app.config['TELEGRAM_BOT_TOKEN'],
            app.config['TELEGRAM_CHAT_ID']
        )
        bot.test_connection()
        print("[OK] Telegram conectado")
    except Exception as e:
        print(f"[WARN] Telegram startup falhou: {e}")

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
