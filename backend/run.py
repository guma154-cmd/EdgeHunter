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

    start_scheduler(app)
    print("[OK] Scheduler iniciado")

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
