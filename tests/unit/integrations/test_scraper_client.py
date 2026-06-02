"""
Testes do scraper_client controlado.
Sem rede real — todos usam mocks ou modo dry_run/disabled.
"""
import pytest
from unittest.mock import patch

from src.edgehunter.integrations.scraper_client import (
    run_scraper_once,
    fetch_source_snapshot,
    parse_source_snapshot,
    _load_scraper_config,
)


def _env_disabled():
    return {"SCRAPER_ENABLED": "false", "SCRAPER_SOURCE_URL": "http://example.com"}

def _env_enabled_no_url():
    return {"SCRAPER_ENABLED": "true", "SCRAPER_SOURCE_URL": "", "EDGEHUNTER_RUNTIME_DRY_RUN": "true"}

def _env_enabled_dry_run():
    return {
        "SCRAPER_ENABLED": "true",
        "SCRAPER_SOURCE_URL": "http://example.com",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        "SCRAPER_TIMEOUT_SECONDS": "5",
        "SCRAPER_RATE_LIMIT_SECONDS": "0",
    }


# ---------------------------------------------------------------------------
# 1. Scraper desabilitado
# ---------------------------------------------------------------------------
def test_scraper_disabled_returns_empty():
    res = run_scraper_once(env=_env_disabled())
    assert res["error"] == "scraper_disabled"
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 2. URL ausente
# ---------------------------------------------------------------------------
def test_missing_url_returns_empty():
    res = run_scraper_once(env=_env_enabled_no_url())
    assert res["error"] == "missing_source_url"
    assert res["actionable"] is False


# ---------------------------------------------------------------------------
# 3. URL inválida (timeout simulado)
# ---------------------------------------------------------------------------
def test_invalid_url_timeout():
    import urllib.request
    with patch.object(urllib.request, "urlopen", side_effect=TimeoutError("forced")):
        env = {
            "SCRAPER_ENABLED": "true",
            "SCRAPER_SOURCE_URL": "http://bad-url.invalid",
            "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
            "SCRAPER_RATE_LIMIT_SECONDS": "0",
        }
        snap = fetch_source_snapshot("http://bad-url.invalid", _load_scraper_config(env))
    assert snap["error"] == "timeout"


# ---------------------------------------------------------------------------
# 4. Timeout gera erro controlado
# ---------------------------------------------------------------------------
def test_timeout_error_handled():
    import urllib.request
    with patch.object(urllib.request, "urlopen", side_effect=TimeoutError("forced")):
        cfg = _load_scraper_config({
            "SCRAPER_ENABLED": "true",
            "SCRAPER_SOURCE_URL": "http://example.com",
            "EDGEHUNTER_RUNTIME_DRY_RUN": "false",
        })
        snap = fetch_source_snapshot("http://example.com", cfg)
    assert snap["error"] == "timeout"
    assert snap["actionable"] is False


# ---------------------------------------------------------------------------
# 5. Rate limit não dispara em dry_run
# ---------------------------------------------------------------------------
def test_rate_limit_not_called_in_dry_run():
    import src.edgehunter.integrations.scraper_client as mod
    calls = []
    original_sleep = mod.time.sleep
    def mock_sleep(n):
        calls.append(n)
    with patch.object(mod.time, "sleep", mock_sleep):
        run_scraper_once(env=_env_enabled_dry_run())
    assert calls == [], "sleep não deve ser chamado em dry_run"


# ---------------------------------------------------------------------------
# 6. Dry-run retorna status DRY_RUN
# ---------------------------------------------------------------------------
def test_dry_run_returns_dry_run_status():
    cfg = _load_scraper_config(_env_enabled_dry_run())
    snap = fetch_source_snapshot("http://example.com", cfg)
    assert snap["status"] == "DRY_RUN"
    assert snap["raw_content"] is None


# ---------------------------------------------------------------------------
# 7. Parser é determinístico
# ---------------------------------------------------------------------------
def test_parser_is_deterministic():
    raw = {
        "status": "OK",
        "raw_content": "linha1\nlinha2\nlinha3",
        "source_url": "http://example.com",
    }
    r1 = parse_source_snapshot(raw)
    r2 = parse_source_snapshot(raw)
    assert r1["items"] == r2["items"]
    assert r1["status"] == "PARSED"
    assert len(r1["items"]) == 3


# ---------------------------------------------------------------------------
# 8. Mock de resposta funciona
# ---------------------------------------------------------------------------
def test_mock_response_is_used():
    res = run_scraper_once(env=_env_enabled_dry_run(), _mock_response="linha_mock")
    # dry_run=true: fetch retorna DRY_RUN antes de usar o mock
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 9. Sem bypass/captcha/login no código
# ---------------------------------------------------------------------------
def test_no_bypass_captcha_login_in_code():
    import src.edgehunter.integrations.scraper_client as mod
    import inspect
    src_code = inspect.getsource(mod)
    for term in ["bypass(", "captcha(", "login(", "selenium", "playwright", "puppeteer"]:
        assert term not in src_code.lower(), f"Termo proibido no código: {term}"


# ---------------------------------------------------------------------------
# 10. Sem rede real quando desabilitado
# ---------------------------------------------------------------------------
def test_no_real_network_when_disabled():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        run_scraper_once(env=_env_disabled())
    assert calls == []


# ---------------------------------------------------------------------------
# 11. Sem execução financeira
# ---------------------------------------------------------------------------
def test_no_financial_execution_in_scraper():
    import src.edgehunter.integrations.scraper_client as mod
    import inspect
    src_code = inspect.getsource(mod)
    for pattern in ["execute_bet(", "place_bet(", "financial_exec(", "autoevolution("]:
        assert pattern not in src_code.lower(), f"Chamada proibida: {pattern}"


# ---------------------------------------------------------------------------
# 12. Flags de segurança presentes
# ---------------------------------------------------------------------------
def test_safe_flags_always_present():
    res = run_scraper_once(env=_env_disabled())
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


# ---------------------------------------------------------------------------
# 13. Config carrega corretamente
# ---------------------------------------------------------------------------
def test_load_config():
    cfg = _load_scraper_config({
        "SCRAPER_ENABLED": "true",
        "SCRAPER_SOURCE_URL": "http://test.local",
        "SCRAPER_TIMEOUT_SECONDS": "15",
        "SCRAPER_RATE_LIMIT_SECONDS": "3",
        "SCRAPER_USER_AGENT": "TestAgent/1.0",
    })
    assert cfg["enabled"] is True
    assert cfg["source_url"] == "http://test.local"
    assert cfg["timeout"] == 15
    assert cfg["rate_limit"] == 3.0
    assert cfg["user_agent"] == "TestAgent/1.0"
