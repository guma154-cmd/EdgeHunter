import os
import sys
from dotenv import load_dotenv

# Adicionar diretório atual ao path
sys.path.append(os.getcwd())

load_dotenv()

from app import create_app

print("--- Iniciando Ciclo Forçado do Scheduler ---")
try:
    app = create_app()
    with app.app_context():
        from app.data.scheduler import _fetch_odds_task
        print("Executando _fetch_odds_task...")
        _fetch_odds_task(app)
        print("Tarefa concluída.")
except Exception as e:
    print(f"ERRO NO CICLO: {e}")

print("--- Fim do Ciclo ---")
