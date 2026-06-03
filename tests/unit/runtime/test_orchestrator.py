"""
Testes do orquestrador controlado.
Sem loop infinito — todos usam max_cycles=1.
Sem rede real — todos usam mocks ou estado desabilitado.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.edgehunter.runtime.orchestrator import (
    run_runtime,
    run_one_cycle,
    _load_runtime_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_disabled():
    return {
        "EDGEHUNTER_RUNTIME_ENABLED": "false",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
    }

def _env_dry_run():
    return {
        "EDGEHUNTER_RUNTIME_ENABLED": "true",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
        "SCRAPER_ENABLED": "false",
        "GEMINI_ENABLED": "false",
        "TELEGRAM_ENABLED": "false",
    }

def _env_active_1_cycle():
    return {
        "EDGEHUNTER_RUNTIME_ENABLED": "true",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
        "SCRAPER_ENABLED": "false",
        "GEMINI_ENABLED": "false",
        "TELEGRAM_ENABLED": "false",
    }

def _mock_send_ok(token, chat_id, text, config):
    return {"sent": True, "is_simulated": True, "actionable": False,
            "not_operational_advice": True, "error": None, "message_text": text}


# ---------------------------------------------------------------------------
# 1. Runtime desabilitado
# ---------------------------------------------------------------------------
def test_runtime_disabled():
    summary = run_runtime(env=_env_disabled())
    assert summary["enabled"] is False
    assert summary["shutdown_reason"] == "runtime_disabled"
    assert summary["cycles_executed"] == 0
    assert summary["actionable"] is False


# ---------------------------------------------------------------------------
# 2. Dry-run executa ciclo sem chamar integrações externas
# ---------------------------------------------------------------------------
def test_dry_run_cycle_no_external_calls():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        summary = run_runtime(env=_env_dry_run())
    assert calls == []
    assert summary["cycles_executed"] == 1
    assert summary["cycles"][0]["dry_run"] is True


# ---------------------------------------------------------------------------
# 3. Ciclo único encerra corretamente
# ---------------------------------------------------------------------------
def test_single_cycle_completes():
    summary = run_runtime(env=_env_active_1_cycle())
    assert summary["cycles_executed"] == 1
    assert summary["shutdown_reason"] == "max_cycles_reached:1"
    assert summary["actionable"] is False


# ---------------------------------------------------------------------------
# 4. max_cycles encerra o loop
# ---------------------------------------------------------------------------
def test_max_cycles_enforced():
    env = {**_env_active_1_cycle(), "EDGEHUNTER_RUNTIME_MAX_CYCLES": "3"}
    summary = run_runtime(env=env)
    assert summary["cycles_executed"] == 3
    assert "max_cycles_reached:3" in summary["shutdown_reason"]


# ---------------------------------------------------------------------------
# 5. Erro no scraper não derruba o runtime
# ---------------------------------------------------------------------------
def test_scraper_error_does_not_crash_runtime():
    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               side_effect=RuntimeError("scraper down")):
        env = {**_env_active_1_cycle(), "SCRAPER_ENABLED": "true", "SCRAPER_SOURCE_URL": "http://x.com"}
        summary = run_runtime(env=env)
    assert summary["cycles_executed"] == 1
    cycle = summary["cycles"][0]
    assert "ERROR" in cycle.get("scraper_status", "")


# ---------------------------------------------------------------------------
# 6. Erro no Gemini gera fallback
# ---------------------------------------------------------------------------
def test_gemini_error_generates_fallback():
    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               return_value={"status": "PARSED", "items": ["jogo 1"]}):
        with patch("src.edgehunter.integrations.gemini_client.validate_with_gemini",
                   side_effect=RuntimeError("gemini down")):
            env = {**_env_active_1_cycle(), "GEMINI_ENABLED": "true", "GEMINI_API_KEY": "FAKE"}
            summary = run_runtime(env=env)
    assert summary["cycles_executed"] == 1
    cycle = summary["cycles"][0]
    assert "ERROR" in cycle.get("gemini_status", "")


# ---------------------------------------------------------------------------
# 7. Erro no Telegram é registrado mas não derruba runtime
# ---------------------------------------------------------------------------
def test_telegram_error_is_logged():
    def failing_send(token, chat_id, text, config):
        raise RuntimeError("telegram down")

    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               return_value={"status": "PARSED", "items": ["jogo 1"]}):
        env = {**_env_active_1_cycle(), "TELEGRAM_ENABLED": "true",
               "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}
        summary = run_runtime(env=env, _mock_send=failing_send)
    assert summary["cycles_executed"] == 1
    cycle = summary["cycles"][0]
    assert "ERROR" in cycle.get("telegram_status", "")


# ---------------------------------------------------------------------------
# 8. Sem loop infinito (max_cycles obrigatório em testes)
# ---------------------------------------------------------------------------
def test_no_infinite_loop():
    env = {**_env_active_1_cycle(), "EDGEHUNTER_RUNTIME_MAX_CYCLES": "2"}
    import time
    calls = []
    def mock_sleep(n):
        calls.append(n)
    with patch.object(time, "sleep", mock_sleep):
        summary = run_runtime(env=env)
    assert summary["cycles_executed"] == 2
    assert len(calls) == 0  # interval=0 então sleep não é chamado


# ---------------------------------------------------------------------------
# 9. Não autoaplica threshold
# ---------------------------------------------------------------------------
def test_no_threshold_autoapply():
    import src.edgehunter.runtime.orchestrator as mod
    import inspect
    src_code = inspect.getsource(mod)
    for term in ["autoapply_threshold(", "apply_threshold(", "set_threshold("]:
        assert term not in src_code.lower(), f"Chamada proibida: {term}"


# ---------------------------------------------------------------------------
# 10. Não executa ação financeira
# ---------------------------------------------------------------------------
def test_no_financial_execution():
    import src.edgehunter.runtime.orchestrator as mod
    import inspect
    src_code = inspect.getsource(mod)
    for term in ["execute_bet(", "place_bet(", "financial_exec(", "autoevolution("]:
        assert term not in src_code.lower(), f"Chamada proibida: {term}"


# ---------------------------------------------------------------------------
# 11. Flags de segurança sempre presentes
# ---------------------------------------------------------------------------
def test_safe_flags_always_present():
    summary = run_runtime(env=_env_disabled())
    assert summary["actionable"] is False
    assert summary["not_operational_advice"] is True
    assert summary["is_simulated"] is True


# ---------------------------------------------------------------------------
# 12. Config carrega corretamente
# ---------------------------------------------------------------------------
def test_load_runtime_config():
    cfg = _load_runtime_config({
        "EDGEHUNTER_RUNTIME_ENABLED": "true",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "5",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "60",
    })
    assert cfg["enabled"] is True
    assert cfg["dry_run"] is False
    assert cfg["max_cycles"] == 5
    assert cfg["interval_seconds"] == 60


# ---------------------------------------------------------------------------
# 13. KeyboardInterrupt encerra limpo
# ---------------------------------------------------------------------------
def test_keyboard_interrupt_clean_shutdown():
    cycle_count = 0

    def mock_cycle(env=None, _mock_send=None, notified_set=None):
        nonlocal cycle_count
        cycle_count += 1
        if cycle_count >= 2:
            raise KeyboardInterrupt
        return {"dry_run": False, "actionable": False, "not_operational_advice": True, "is_simulated": True}

    with patch("src.edgehunter.runtime.orchestrator.run_one_cycle", mock_cycle):
        env = {
            "EDGEHUNTER_RUNTIME_ENABLED": "true",
            "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
            "EDGEHUNTER_RUNTIME_MAX_CYCLES": "999",
            "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
        }
        summary = run_runtime(env=env)
    assert summary["shutdown_reason"] == "keyboard_interrupt"


# ---------------------------------------------------------------------------
# 14. Pulo do Gemini em Radar EMPTY
# ---------------------------------------------------------------------------
def test_gemini_skipped_on_empty_radar():
    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               return_value={"status": "EMPTY", "items": []}):
        with patch("src.edgehunter.integrations.gemini_client.validate_with_gemini") as mock_gemini:
            env = {
                "EDGEHUNTER_RUNTIME_ENABLED": "true",
                "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
                "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
                "GEMINI_SKIP_WHEN_RADAR_EMPTY": "true",
                "TELEGRAM_NOTIFY_EMPTY_CYCLES": "true", # Garante que entra no loop de notificação
            }
            summary = run_runtime(env=env)
            assert summary["cycles"][0]["gemini_status"] == "SKIPPED"
            mock_gemini.assert_not_called()


# ---------------------------------------------------------------------------
# 15. Supressão de Telegram em Radar EMPTY
# ---------------------------------------------------------------------------
def test_telegram_suppressed_on_empty_radar():
    import src.edgehunter.runtime.orchestrator as orch
    # Força TS para evitar heartbeat no primeiro ciclo para este teste
    orch._LAST_HEARTBEAT_TS = 9999999999.0

    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               return_value={"status": "EMPTY", "items": []}):
        with patch("src.edgehunter.integrations.telegram_notifier.notify_runtime_status") as mock_tel:
            env = {
                "EDGEHUNTER_RUNTIME_ENABLED": "true",
                "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
                "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
                "TELEGRAM_NOTIFY_EMPTY_CYCLES": "false",
                "TELEGRAM_HEARTBEAT_ENABLED": "true",
                "TELEGRAM_HEARTBEAT_INTERVAL_MINUTES": "360",
            }
            summary = run_runtime(env=env)
            assert summary["cycles"][0]["telegram_status"] == "SUPPRESSED"
            mock_tel.assert_not_called()

    # Limpa estado para próximos testes
    orch._LAST_HEARTBEAT_TS = 0.0


# ---------------------------------------------------------------------------
# 16. Heartbeat enviado mesmo em Radar EMPTY
# ---------------------------------------------------------------------------
def test_heartbeat_sent_on_empty_radar():
    import src.edgehunter.runtime.orchestrator as orch
    orch._LAST_HEARTBEAT_TS = 0.0 # Gatilha heartbeat imediato

    with patch("src.edgehunter.integrations.scraper_client.run_scraper_once",
               return_value={"status": "EMPTY", "items": []}):
        with patch("src.edgehunter.integrations.telegram_notifier.notify_runtime_status",
                   return_value={"sent": True}) as mock_tel:
            env = {
                "EDGEHUNTER_RUNTIME_ENABLED": "true",
                "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
                "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
                "TELEGRAM_NOTIFY_EMPTY_CYCLES": "false",
                "TELEGRAM_HEARTBEAT_ENABLED": "true",
            }
            summary = run_runtime(env=env)
            assert summary["cycles"][0]["telegram_status"] == "SENT"
            mock_tel.assert_called_once()
            # Verifica se is_heartbeat foi passado
            args, kwargs = mock_tel.call_args
            assert args[0]["is_heartbeat"] is True
