"""
Teste ponta a ponta controlado do EdgeHunter.

Valida o ciclo completo com mocks:
- API via TestClient
- Scraper mock
- Gemini desabilitado (fallback)
- Telegram mock
- Runtime 1 ciclo

Sem rede real, sem execução financeira, sem AutoEvolution.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures de ambiente
# ---------------------------------------------------------------------------

@pytest.fixture
def e2e_env():
    """Ambiente E2E controlado com todas as integrações via mock/disabled."""
    return {
        "EDGEHUNTER_RUNTIME_ENABLED": "true",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "1",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
        "GEMINI_ENABLED": "false",
        "SCRAPER_ENABLED": "true",
        "SCRAPER_SOURCE_URL": "http://mock.local",
        "SCRAPER_RATE_LIMIT_SECONDS": "0",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "false",  # live para exercitar os passos
        "TELEGRAM_ENABLED": "true",
        "TELEGRAM_BOT_TOKEN": "mock_token",
        "TELEGRAM_CHAT_ID": "mock_chat",
    }


def _mock_telegram_send(token, chat_id, text, config):
    """Mock do Telegram — captura mensagem sem envio real."""
    return {
        "sent": True,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True,
        "error": None,
        "message_text": text,
    }


# ---------------------------------------------------------------------------
# 1. Config carrega corretamente em E2E
# ---------------------------------------------------------------------------
def test_e2e_config_loads(e2e_env):
    from src.edgehunter.runtime.orchestrator import _load_runtime_config
    cfg = _load_runtime_config(e2e_env)
    assert cfg["enabled"] is True
    assert cfg["max_cycles"] == 1
    assert cfg["interval_seconds"] == 0


# ---------------------------------------------------------------------------
# 2. API sobe via TestClient
# ---------------------------------------------------------------------------
def test_e2e_api_health():
    from fastapi.testclient import TestClient
    from src.edgehunter.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("data", {}).get("status") in ("ok", "healthy", "read_only")


# ---------------------------------------------------------------------------
# 3. Scraper mock roda sem rede real
# ---------------------------------------------------------------------------
def test_e2e_scraper_mock_no_network(e2e_env):
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)

    from src.edgehunter.integrations.scraper_client import run_scraper_once
    with patch.object(socket.socket, "connect", mock_connect):
        result = run_scraper_once(
            env={**e2e_env, "EDGEHUNTER_RUNTIME_DRY_RUN": "true"},
            _mock_response="match tecnico\nresultado local"
        )
    assert calls == []
    assert result["actionable"] is False
    assert result["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 4. Gemini desabilitado usa fallback
# ---------------------------------------------------------------------------
def test_e2e_gemini_fallback(e2e_env):
    from src.edgehunter.integrations.gemini_client import validate_with_gemini
    result = validate_with_gemini("analise tecnica", env={**e2e_env, "GEMINI_ENABLED": "false"})
    assert result["fallback_reason"] == "gemini_disabled"
    assert result["actionable"] is False


# ---------------------------------------------------------------------------
# 5. Telegram mock recebe mensagem técnica
# ---------------------------------------------------------------------------
def test_e2e_telegram_mock_receives_message(e2e_env):
    from src.edgehunter.integrations.telegram_notifier import notify_runtime_status
    result = notify_runtime_status(
        {"status": "E2E_TEST", "cycles": 1},
        env=e2e_env,
        _mock_send=_mock_telegram_send,
    )
    assert result["sent"] is True
    assert result["actionable"] is False
    assert "E2E_TEST" in result["message_text"]


# ---------------------------------------------------------------------------
# 6. Runtime executa 1 ciclo completo com mocks
# ---------------------------------------------------------------------------
def test_e2e_runtime_one_cycle(e2e_env):
    with patch(
        "src.edgehunter.integrations.scraper_client.run_scraper_once",
        return_value={"status": "PARSED", "items": ["dado1"], "actionable": False,
                      "not_operational_advice": True, "is_simulated": True}
    ):
        from src.edgehunter.runtime.orchestrator import run_runtime
        summary = run_runtime(env=e2e_env, _mock_send=_mock_telegram_send)

    assert summary["cycles_executed"] == 1
    assert summary["actionable"] is False
    assert summary["not_operational_advice"] is True
    assert summary["is_simulated"] is True


# ---------------------------------------------------------------------------
# 7. Dashboard responde
# ---------------------------------------------------------------------------
def test_e2e_api_readiness():
    from fastapi.testclient import TestClient
    from src.edgehunter.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/readiness", headers={"x-api-key": "invalid"})
    assert resp.status_code in (200, 401, 403)


# ---------------------------------------------------------------------------
# 8. Sem rede real no E2E completo
# ---------------------------------------------------------------------------
def test_e2e_no_real_network(e2e_env):
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)

    with patch(
        "src.edgehunter.integrations.scraper_client.run_scraper_once",
        return_value={"status": "OK", "items": [], "actionable": False,
                      "not_operational_advice": True, "is_simulated": True}
    ), patch.object(socket.socket, "connect", mock_connect):
        from src.edgehunter.runtime.orchestrator import run_runtime
        run_runtime(env=e2e_env, _mock_send=_mock_telegram_send)

    assert calls == []


# ---------------------------------------------------------------------------
# 9. Sem execução financeira no E2E
# ---------------------------------------------------------------------------
def test_e2e_no_financial_execution(e2e_env):
    with patch(
        "src.edgehunter.integrations.scraper_client.run_scraper_once",
        return_value={"status": "OK", "items": [], "actionable": False,
                      "not_operational_advice": True, "is_simulated": True}
    ):
        from src.edgehunter.runtime.orchestrator import run_runtime
        summary = run_runtime(env=e2e_env, _mock_send=_mock_telegram_send)

    # Verificar que nenhum ciclo tem flag acionável
    for cycle in summary["cycles"]:
        assert cycle.get("actionable") is False, f"Ciclo acionável detectado: {cycle}"


# ---------------------------------------------------------------------------
# 10. Sem AutoEvolution no E2E
# ---------------------------------------------------------------------------
def test_e2e_no_autoevolution():
    import src.edgehunter.runtime.orchestrator as mod
    import inspect
    src_code = inspect.getsource(mod)
    # Ignorar docstrings
    import ast
    tree = ast.parse(src_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id.lower() not in ("autoevolution", "autoapply_threshold")
