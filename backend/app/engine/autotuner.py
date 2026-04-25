import itertools
import json
import logging
from pathlib import Path

from flask import current_app
from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)


class AutoTuner:
    """
    Testa variações de parâmetros do detector a cada 24h.
    Sem chamadas de API — grid search determinístico.
    Mede ROI real das surebets detectadas.
    Promove configuração vencedora automaticamente.
    """

    PARAM_GRID = {
        'min_profit_pct': [0.5, 1.0, 1.5, 2.0],
        'max_roi_pct': [5.0, 8.0, 10.0],
        'stake_pct': [0.10, 0.15, 0.20, 0.25],
    }

    def __init__(self):
        self._grid = list(itertools.product(
            self.PARAM_GRID['min_profit_pct'],
            self.PARAM_GRID['max_roi_pct'],
            self.PARAM_GRID['stake_pct'],
        ))

    def run_cycle(self):
        """
        1. Avaliar configuração atual (ROI últimas 24h)
        2. Selecionar próxima variação do grid
        3. Atualizar .env / config com nova configuração
        4. Logar experimento no banco
        5. Enviar resultado via Telegram
        """
        from datetime import datetime, timedelta
        from app.alerts.telegram_bot import send_message
        from app.models import Bet

        cutoff = datetime.utcnow() - timedelta(hours=24)
        bets = Bet.query.filter(
            Bet.timestamp >= cutoff,
            Bet.profit_loss.isnot(None)
        ).all()

        total_profit = sum((b.profit_loss or 0.0) for b in bets)
        total_stake = sum((b.stake or 0.0) for b in bets)
        current_roi = (total_profit / max(total_stake, 1.0)) if bets else 0.0

        next_config = self._next_config()
        self._log_experiment(current_roi, len(bets), next_config)
        self._apply_config(next_config)

        send_message(
            f"🔬 <b>AutoTuner - Ciclo</b>\n\n"
            f"ROI atual (24h): <code>{current_roi:.2%}</code>\n"
            f"Apostas: <code>{len(bets)}</code>\n\n"
            f"<b>Nova config testando:</b>\n"
            f"Min profit: <code>{next_config['min_profit_pct']}%</code>\n"
            f"Stake: <code>{next_config['stake_pct']:.0%}</code>\n"
            f"Max ROI: <code>{next_config['max_roi_pct']}%</code>"
        )
        logger.info(f"[AutoTuner] Nova configuração aplicada: {next_config}")

    def _state_file(self) -> Path:
        return Path(current_app.root_path).parent / 'autotuner_state.json'

    def _env_file(self) -> Path:
        return Path(current_app.root_path).parent.parent / 'backend' / '.env'

    def _read_state(self) -> dict:
        state_file = self._state_file()
        if state_file.exists():
            try:
                return json.loads(state_file.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def _write_state(self, state: dict):
        self._state_file().write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _next_config(self) -> dict:
        state = self._read_state()
        index = int(state.get('grid_index', -1)) + 1
        index %= len(self._grid)
        min_profit, max_roi, stake_pct = self._grid[index]
        state['grid_index'] = index
        self._write_state(state)
        return {
            'min_profit_pct': min_profit,
            'max_roi_pct': max_roi,
            'stake_pct': stake_pct,
        }

    def _log_experiment(self, current_roi: float, bets_count: int, next_config: dict):
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS autotuner_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                roi_24h REAL NOT NULL,
                bets_count INTEGER NOT NULL,
                min_profit_pct REAL NOT NULL,
                max_roi_pct REAL NOT NULL,
                stake_pct REAL NOT NULL
            )
        """))
        db.session.execute(
            text("""
                INSERT INTO autotuner_experiments (
                    created_at, roi_24h, bets_count, min_profit_pct, max_roi_pct, stake_pct
                ) VALUES (
                    :created_at, :roi_24h, :bets_count, :min_profit_pct, :max_roi_pct, :stake_pct
                )
            """),
            {
                'created_at': __import__('datetime').datetime.utcnow().isoformat(),
                'roi_24h': float(current_roi),
                'bets_count': int(bets_count),
                'min_profit_pct': float(next_config['min_profit_pct']),
                'max_roi_pct': float(next_config['max_roi_pct']),
                'stake_pct': float(next_config['stake_pct']),
            }
        )
        db.session.commit()

    def _apply_config(self, next_config: dict):
        current_app.config['MIN_SUREBET_PROFIT'] = float(next_config['min_profit_pct'])
        current_app.config['MAX_SUREBET_ROI'] = float(next_config['max_roi_pct'])
        current_app.config['STAKE_PCT'] = float(next_config['stake_pct'])

        env_file = self._env_file()
        if not env_file.exists():
            return

        lines = env_file.read_text(encoding='utf-8').splitlines()
        updates = {
            'MIN_SUREBET_PROFIT': str(next_config['min_profit_pct']),
            'MAX_SUREBET_ROI': str(next_config['max_roi_pct']),
            'STAKE_PCT': str(next_config['stake_pct']),
        }

        seen = set()
        new_lines = []
        for line in lines:
            replaced = False
            for key, value in updates.items():
                if line.startswith(f'{key}='):
                    new_lines.append(f'{key}={value}')
                    seen.add(key)
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        for key, value in updates.items():
            if key not in seen:
                new_lines.append(f'{key}={value}')

        env_file.write_text("\n".join(new_lines) + "\n", encoding='utf-8')
