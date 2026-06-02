"""
Testes do telegram_notifier controlado.
Sem rede real — todos usam mock_send ou estado desabilitado.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.edgehunter.integrations.telegram_notifier import (
    notify_runtime_status,
    notify_signal_summary,
    build_telegram_message,
    send_telegram_message,
    _contains_forbidden_message,
    _load_telegram_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_ok_send(token, chat_id, text, config):
    return {"sent": True, "is_simulated": True, "actionable": False,
            "not_operational_advice": True, "error": None, "message_text": text}

def _env_disabled():
    return {"TELEGRAM_ENABLED": "false", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}

def _env_enabled_no_token():
    return {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "123"}

def _env_enabled_no_chat():
    return {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": ""}

def _env_enabled():
    return {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}


# ---------------------------------------------------------------------------
# 1. Telegram desabilitado
# ---------------------------------------------------------------------------
def test_telegram_disabled():
    res = notify_runtime_status({"status": "HEALTHY"}, env=_env_disabled())
    assert res["error"] == "telegram_disabled"
    assert res["sent"] is False
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 2. Token ausente
# ---------------------------------------------------------------------------
def test_missing_token_returns_error():
    res = notify_runtime_status({"status": "HEALTHY"}, env=_env_enabled_no_token())
    assert res["error"] == "missing_bot_token"
    assert res["sent"] is False


# ---------------------------------------------------------------------------
# 3. Chat ID ausente
# ---------------------------------------------------------------------------
def test_missing_chat_id_returns_error():
    res = notify_runtime_status({"status": "HEALTHY"}, env=_env_enabled_no_chat())
    assert res["error"] == "missing_chat_id"
    assert res["sent"] is False


# ---------------------------------------------------------------------------
# 4. Timeout gera erro controlado
# ---------------------------------------------------------------------------
def test_timeout_handled():
    import urllib.request
    cfg = _load_telegram_config(_env_enabled())
    with patch.object(urllib.request, "urlopen", side_effect=TimeoutError("forced")):
        res = send_telegram_message("tok", "123", "status tecnico", cfg)
    assert res["error"] == "timeout"
    assert res["sent"] is False


# ---------------------------------------------------------------------------
# 5. Mensagem técnica válida é enviada com mock
# ---------------------------------------------------------------------------
def test_valid_technical_message_sent_with_mock():
    res = notify_runtime_status(
        {"cycles": 5, "status": "HEALTHY", "label": "GREEN_SIM"},
        env=_env_enabled(),
        _mock_send=_mock_ok_send,
    )
    assert res["sent"] is True
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 6. Mensagem proibida é bloqueada — stake
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("forbidden", [
    "stake de 10 unidades",
    "kelly criterion recomendado",
    "bankroll management",
    "apostar agora",
    "execute trade",
    "place_bet confirmado",
])
def test_forbidden_message_blocked(forbidden):
    cfg = _load_telegram_config(_env_enabled())
    res = send_telegram_message("tok", "123", f"alerta: {forbidden}", cfg)
    assert res["error"] == "forbidden_content_in_message"
    assert res["sent"] is False


# ---------------------------------------------------------------------------
# 7. Mock de envio funciona — sem rede real
# ---------------------------------------------------------------------------
def test_mock_send_no_network():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        notify_runtime_status({"status": "ok"}, env=_env_enabled(), _mock_send=_mock_ok_send)
    assert calls == []


# ---------------------------------------------------------------------------
# 8. Sem rede real quando desabilitado
# ---------------------------------------------------------------------------
def test_no_real_network_when_disabled():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        notify_runtime_status({"status": "ok"}, env=_env_disabled())
    assert calls == []


# ---------------------------------------------------------------------------
# 9. Sem execução financeira no notifier
# ---------------------------------------------------------------------------
def test_no_financial_execution_in_notifier():
    import src.edgehunter.integrations.telegram_notifier as mod
    import inspect
    src_code = inspect.getsource(mod)
    for pattern in ["execute_bet(", "place_bet(", "financial_exec(", "autoevolution("]:
        assert pattern not in src_code.lower(), f"Chamada proibida: {pattern}"


# ---------------------------------------------------------------------------
# 10. build_telegram_message bloqueia valores proibidos em data
# ---------------------------------------------------------------------------
def test_build_message_blocks_forbidden_data_values():
    msg = build_telegram_message("runtime_status", {
        "status": "HEALTHY",
        "info": "stake de 50 unidades",  # proibido
    })
    assert "[BLOCKED]" in msg
    assert "stake" not in msg.lower().replace("[blocked]", "")


# ---------------------------------------------------------------------------
# 11. build_telegram_message inclui label técnico sem bloqueio
# ---------------------------------------------------------------------------
def test_build_message_allows_technical_labels():
    msg = build_telegram_message("signal_summary", {
        "label": "GREEN_SIM",
        "home": "Time A",
        "away": "Time B",
        "selection": "Empate",
        "calibrated_assertiveness": "65.5",
        "reliability_level": "Média",
        "trend_status": "Neutro",
        "offered_odds": "3.10",
        "expected_value": "5.0",
        "source": "Scraper",
        "signal_id": "1234",
    })
    assert "🟢 GREEN" in msg
    assert "Time A x Time B" in msg
    assert "Hipótese: Empate" in msg
    assert "Status: paper trading / não operacional" in msg
    assert "GREEN_SIM" not in msg  # Apenas 🟢 GREEN aparece no texto
    assert "[BLOCKED]" not in msg


def test_build_message_red_sim_template():
    msg = build_telegram_message("signal_summary", {
        "label": "RED_SIM",
        "selection": "Visitante",
    })
    assert "🔴 RED" in msg
    assert "Hipótese rejeitada: Visitante" in msg
    assert "Status: paper trading / não operacional" in msg


# ---------------------------------------------------------------------------
# 12. notify_signal_summary funciona com mock
# ---------------------------------------------------------------------------
def test_notify_signal_summary_with_mock():
    res = notify_signal_summary(
        {"label": "RED_SIM", "count": 3},
        env=_env_enabled(),
        _mock_send=_mock_ok_send,
    )
    assert res["sent"] is True
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 13. _contains_forbidden_message detecta termos proibidos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("status runtime HEALTHY", False),
    ("GREEN_SIM detectado", False),
    ("stake de 5 unidades", True),
    ("apostar agora", True),
    ("bankroll management ativo", True),
])
def test_contains_forbidden_message(text, expected):
    assert _contains_forbidden_message(text) == expected


# ---------------------------------------------------------------------------
# 14. Flags de segurança presentes
# ---------------------------------------------------------------------------
def test_safe_flags_always_present():
    res = notify_runtime_status({"status": "ok"}, env=_env_disabled())
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True
