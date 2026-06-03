"""
Orquestrador 24/7 controlado.

Habilitado apenas via EDGEHUNTER_RUNTIME_ENABLED=true no .env.
DRY_RUN=true por padrão — nenhuma ação externa ocorre sem flag explícita.
Sem execução financeira, sem autoaplicação de threshold, sem AutoEvolution.
"""
import os
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _load_runtime_config(env: Optional[dict] = None) -> dict:
    e = env or {}

    def get_v(key, default):
        val = e.get(key) if key in e else os.environ.get(key)
        return val if val else default

    return {
        "enabled": str(get_v("EDGEHUNTER_RUNTIME_ENABLED", "false")).lower() == "true",
        "interval_seconds": int(get_v("EDGEHUNTER_RUNTIME_INTERVAL_SECONDS", "300")),
        "max_cycles": int(get_v("EDGEHUNTER_RUNTIME_MAX_CYCLES", "0")) if get_v("EDGEHUNTER_RUNTIME_MAX_CYCLES", "") else None,
        "dry_run": str(get_v("EDGEHUNTER_RUNTIME_DRY_RUN", "true")).lower() == "true",
        "notify_empty": str(get_v("TELEGRAM_NOTIFY_EMPTY_CYCLES", "false")).lower() == "true",
        "heartbeat_enabled": str(get_v("TELEGRAM_HEARTBEAT_ENABLED", "true")).lower() == "true",
        "heartbeat_interval_minutes": int(get_v("TELEGRAM_HEARTBEAT_INTERVAL_MINUTES", "360")),
        "skip_gemini_empty": str(get_v("GEMINI_SKIP_WHEN_RADAR_EMPTY", "true")).lower() == "true",
    }


def _run_scraper_step(env: dict, cycle_log: dict) -> dict:
    """Executa passo de scraping com tratamento de erro isolado."""
    try:
        from src.edgehunter.integrations.scraper_client import run_scraper_once
        result = run_scraper_once(env=env)
        cycle_log["scraper_status"] = result.get("status", "EMPTY")
        return result
    except Exception as e:
        logger.warning(f"Scraper step failed: {e}")
        cycle_log["scraper_status"] = f"ERROR:{type(e).__name__}"
        return {"status": "ERROR", "items": [], "actionable": False}


def _run_gemini_step(prompt: str, env: dict, cycle_log: dict) -> dict:
    """Executa passo Gemini com fallback isolado."""
    try:
        from src.edgehunter.integrations.gemini_client import validate_with_gemini
        result = validate_with_gemini(prompt, env=env)
        cycle_log["gemini_status"] = "OK" if result.get("valid") else result.get("fallback_reason", "FALLBACK")
        return result
    except Exception as e:
        logger.warning(f"Gemini step failed: {e}")
        cycle_log["gemini_status"] = f"ERROR:{type(e).__name__}"
        return {"valid": False, "parsed": {"label": "UNRESOLVED"}, "actionable": False}


def _run_telegram_step(status_data: dict, env: dict, cycle_log: dict, _mock_send=None) -> None:
    """Envia notificação Telegram com erro isolado."""
    try:
        from src.edgehunter.integrations.telegram_notifier import notify_runtime_status
        result = notify_runtime_status(status_data, env=env, _mock_send=_mock_send)
        cycle_log["telegram_status"] = "SENT" if result.get("sent") else result.get("error", "NOT_SENT")
    except Exception as e:
        logger.warning(f"Telegram step failed: {e}")
        cycle_log["telegram_status"] = f"ERROR:{type(e).__name__}"


_LAST_HEARTBEAT_TS = 0.0


def run_one_cycle(env: Optional[dict] = None, _mock_send=None, notified_set: Optional[set] = None) -> dict:
    """
    Executa um único ciclo do runtime.
    Nunca executa ação financeira.
    Nunca autoaplica threshold.
    """
    global _LAST_HEARTBEAT_TS
    config = _load_runtime_config(env)
    cycle_log = {
        "dry_run": config["dry_run"],
        "scraper_status": "SKIPPED",
        "gemini_status": "SKIPPED",
        "telegram_status": "SKIPPED",
        "actionable": False,
        "not_operational_advice": True,
        "is_simulated": True,
    }

    if notified_set is None:
        notified_set = set()

    if config["dry_run"]:
        cycle_log["note"] = "dry_run=true — nenhuma ação externa executada"
        logger.info("Cycle: DRY_RUN mode — skipping all external steps")
        return cycle_log

    # 1. Scraper
    scraper_result = _run_scraper_step(env or {}, cycle_log)

    # 2. Gemini (com prompt técnico genérico)
    gemini_result = {"valid": False, "parsed": {"label": "UNRESOLVED"}, "actionable": False}
    if cycle_log["scraper_status"] == "EMPTY" and config["skip_gemini_empty"]:
        cycle_log["gemini_status"] = "SKIPPED"
        logger.info("Cycle: Radar EMPTY — skipping Gemini step")
    else:
        if os.environ.get("RADAR_PROFILE") == "test_active_leagues":
            import json
            try:
                data = json.loads(scraper_result["items"][0])
                event = data["events"][0]
                home = event.get("strHomeTeam", "Home")
                away = event.get("strAwayTeam", "Away")
            except Exception:
                home = "Home"
                away = "Away"

            gemini_result = {
                "valid": True,
                "parsed": {
                    "signal_id": "TEST_AL_001",
                    "home": home,
                    "away": away,
                    "selection": "Mandante",
                    "calibrated_assertiveness": "80.0",
                    "offered_odds": "2.00",
                    "source": "TheSportsDB (Test Profile)"
                },
                "actionable": False
            }
            cycle_log["gemini_status"] = "OK_SIMULATED"
            logger.info("Cycle: RADAR_PROFILE=test_active_leagues — injecting mock signal")
        else:
            gemini_result = _run_gemini_step("analise tecnica de dados locais", env or {}, cycle_log)

    # 3. Telegram: Runtime Status
    now = time.time()
    is_heartbeat = False
    if config["heartbeat_enabled"]:
        # Se passaram X minutos desde o último heartbeat ou se é o primeiro ciclo
        if (now - _LAST_HEARTBEAT_TS) >= (config["heartbeat_interval_minutes"] * 60) or _LAST_HEARTBEAT_TS == 0.0:
            is_heartbeat = True
            _LAST_HEARTBEAT_TS = now

    should_notify = True
    if cycle_log["scraper_status"] == "EMPTY" and not config["notify_empty"] and not is_heartbeat:
        should_notify = False
        cycle_log["telegram_status"] = "SUPPRESSED"
        logger.info("Cycle: Radar EMPTY — suppressing Telegram status notification")

    if should_notify:
        status_data = {
            "cycle": "active",
            "scraper": cycle_log["scraper_status"],
            "gemini": cycle_log["gemini_status"],
            "label": gemini_result.get("parsed", {}).get("label", "UNRESOLVED"),
            "is_heartbeat": is_heartbeat,
        }
        _run_telegram_step(status_data, env or {}, cycle_log, _mock_send=_mock_send)

    # 4. Notificações de Sinais Pendentes e Resolvidos
    from src.edgehunter.runtime.result_resolution_notifications import process_and_notify_signals

    pending_signals = []
    if gemini_result.get("valid") and gemini_result.get("parsed"):
        pending_signals.append(gemini_result.get("parsed"))

    resolved_outcomes = [] # TODO: Conectar com o módulo de extração de resultados (ObservedResult/Outcome Builder) quando estiver pronto

    if os.environ.get("RADAR_PROFILE") == "test_active_leagues" and os.environ.get("SIMULATE_RESULT"):
        sim_res = os.environ.get("SIMULATE_RESULT")
        resolved_outcomes.append({
            "signal_id": "TEST_AL_001",
            "selection": "Mandante",
            "home_score": 2 if sim_res == "GREEN" else 1,
            "away_score": 0 if sim_res == "GREEN" else 2,
        })

    process_and_notify_signals(
        pending_signals=pending_signals,
        resolved_outcomes=resolved_outcomes,
        notified_set=notified_set,
        env=env or {},
        _mock_send=_mock_send
    )

    logger.info(f"Cycle completed: {cycle_log}")
    return cycle_log


def run_runtime(env: Optional[dict] = None, _mock_send=None) -> dict:
    """
    Loop principal do runtime.
    Encerra após max_cycles se configurado.
    Sem loop infinito em testes (use max_cycles).
    """
    config = _load_runtime_config(env)

    summary = {
        "enabled": config["enabled"],
        "cycles_executed": 0,
        "cycles": [],
        "shutdown_reason": None,
        "actionable": False,
        "not_operational_advice": True,
        "is_simulated": True,
    }

    if not config["enabled"]:
        summary["shutdown_reason"] = "runtime_disabled"
        return summary

    cycle_count = 0
    notified_set = set()
    try:
        while True:
            cycle_log = run_one_cycle(env=env, _mock_send=_mock_send, notified_set=notified_set)
            summary["cycles"].append(cycle_log)
            cycle_count += 1
            summary["cycles_executed"] = cycle_count

            if config["max_cycles"] is not None and cycle_count >= config["max_cycles"]:
                summary["shutdown_reason"] = f"max_cycles_reached:{config['max_cycles']}"
                break

            if config["interval_seconds"] > 0 and config["max_cycles"] != 1:
                time.sleep(config["interval_seconds"])

    except KeyboardInterrupt:
        summary["shutdown_reason"] = "keyboard_interrupt"
        logger.info("Runtime: clean shutdown via KeyboardInterrupt")

    return summary
