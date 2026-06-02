"""
Testes do gemini_client controlado.
Sem rede real — todos usam mocks ou o cliente offline padrão.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.edgehunter.integrations.gemini_client import (
    validate_with_gemini,
    _contains_forbidden,
    _load_gemini_config,
    _fake_gemini_validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_disabled():
    return {"GEMINI_ENABLED": "false", "GEMINI_API_KEY": "", "GEMINI_MODEL": "gemini-1.5-flash"}

def _env_enabled_no_key():
    return {"GEMINI_ENABLED": "true", "GEMINI_API_KEY": "", "GEMINI_MODEL": "gemini-1.5-flash"}

def _env_enabled_with_key():
    return {"GEMINI_ENABLED": "true", "GEMINI_API_KEY": "FAKE_KEY", "GEMINI_MODEL": "gemini-1.5-flash"}


# ---------------------------------------------------------------------------
# 1. Gemini desabilitado usa fallback offline
# ---------------------------------------------------------------------------
def test_disabled_uses_fallback():
    res = validate_with_gemini("analise tecnica de odds", env=_env_disabled())
    assert res["fallback_reason"] == "gemini_disabled"
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True
    assert res["is_simulated"] is True
    assert res["valid"] is True


# ---------------------------------------------------------------------------
# 2. Habilitado sem chave retorna fallback controlado
# ---------------------------------------------------------------------------
def test_enabled_without_api_key_returns_controlled_fallback():
    res = validate_with_gemini("analise tecnica", env=_env_enabled_no_key())
    assert res["fallback_reason"] == "missing_api_key"
    assert res["actionable"] is False
    assert res["valid"] is False or res["parsed"]["label"] == "UNRESOLVED"


# ---------------------------------------------------------------------------
# 3. Timeout gera fallback
# ---------------------------------------------------------------------------
def test_timeout_generates_fallback():
    import urllib.request
    with patch.object(urllib.request, "urlopen", side_effect=TimeoutError("forced")):
        res = validate_with_gemini("analise tecnica", env=_env_enabled_with_key())
    assert res["fallback_reason"] == "timeout"
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 4. Resposta inválida gera fallback seguro
# ---------------------------------------------------------------------------
def test_invalid_response_generates_safe_fallback():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"candidates": [{"content": {"parts": [{"text": "!@#$%^"}]}}]}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    import urllib.request
    with patch.object(urllib.request, "urlopen", return_value=mock_resp):
        res = validate_with_gemini("analise tecnica", env=_env_enabled_with_key())
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 5. Resposta com linguagem proibida é bloqueada
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("forbidden_word", [
    "stake", "kelly", "bankroll", "aposta", "place_bet", "lucro"
])
def test_forbidden_content_in_response_is_blocked(forbidden_word):
    raw = f"A análise indica {forbidden_word} de 50 unidades."
    mock_resp = MagicMock()
    mock_resp.read.return_value = (
        f'{{"candidates": [{{"content": {{"parts": [{{"text": "{raw}"}}]}}}}]}}'
    ).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    import urllib.request
    with patch.object(urllib.request, "urlopen", return_value=mock_resp):
        res = validate_with_gemini("analise tecnica", env=_env_enabled_with_key())
    assert res["fallback_reason"] == "forbidden_content_in_response"
    assert res["valid"] is False
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 6. Resultado nunca é actionable
# ---------------------------------------------------------------------------
def test_result_never_actionable():
    res = validate_with_gemini("analise qualquer", env=_env_disabled())
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 7. Sem stake/Kelly/bankroll no resultado
# ---------------------------------------------------------------------------
def test_no_stake_kelly_bankroll_in_result():
    res = validate_with_gemini("analise qualquer", env=_env_disabled())
    res_str = str(res).lower()
    for term in ["stake", "kelly", "bankroll", "wager", "bet_amount"]:
        assert term not in res_str, f"Termo proibido encontrado: {term}"


# ---------------------------------------------------------------------------
# 8. Sem Telegram no cliente
# ---------------------------------------------------------------------------
def test_no_telegram_import():
    import src.edgehunter.integrations.gemini_client as mod
    import inspect
    src_code = inspect.getsource(mod)
    assert "telegram" not in src_code.lower()


# ---------------------------------------------------------------------------
# 9. Sem scheduler no cliente
# ---------------------------------------------------------------------------
def test_no_scheduler_in_gemini_client():
    import src.edgehunter.integrations.gemini_client as mod
    import inspect
    src_code = inspect.getsource(mod)
    assert "scheduler" not in src_code.lower()


# ---------------------------------------------------------------------------
# 10. Sem execução financeira
# ---------------------------------------------------------------------------
def test_no_financial_execution():
    import src.edgehunter.integrations.gemini_client as mod
    import inspect
    src_code = inspect.getsource(mod)
    # Verificar que não há chamadas de execução financeira real
    # (os termos podem aparecer na lista de guardrail, mas não como chamadas de função)
    financial_exec_patterns = ["execute_bet(", "place_bet(", "financial_exec(", "autoevolution("]
    for pattern in financial_exec_patterns:
        assert pattern not in src_code.lower(), f"Chamada proibida no código: {pattern}"


# ---------------------------------------------------------------------------
# 11. Sem rede real nos testes (socket não é aberto)
# ---------------------------------------------------------------------------
def test_no_real_network_when_disabled():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        validate_with_gemini("teste", env=_env_disabled())
    assert calls == []


# ---------------------------------------------------------------------------
# 12. Flags de segurança presentes
# ---------------------------------------------------------------------------
def test_safe_flags_always_present():
    res = validate_with_gemini("analise qualquer", env=_env_disabled())
    assert "is_simulated" in res
    assert "actionable" in res
    assert "not_operational_advice" in res
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 13. _contains_forbidden detecta termos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("análise técnica de mercado", False),
    ("GREEN_SIM detectado", False),
    ("stake de 5 unidades", True),
    ("kelly criterion aplicado", True),
    ("bankroll management", True),
    ("apostar agora", True),
])
def test_contains_forbidden(text, expected):
    assert _contains_forbidden(text) == expected


# ---------------------------------------------------------------------------
# 14. Config carrega corretamente de env dict
# ---------------------------------------------------------------------------
def test_load_gemini_config_from_env_dict():
    cfg = _load_gemini_config({"GEMINI_ENABLED": "true", "GEMINI_API_KEY": "XYZ", "GEMINI_TIMEOUT_SECONDS": "8"})
    assert cfg["enabled"] is True
    assert cfg["api_key"] == "XYZ"
    assert cfg["timeout"] == 8
