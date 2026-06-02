"""
Testes do run_runtime.py.
Sem loop infinito, sem rede real, sem shell perigoso.
"""
import os
import pytest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# 1. Script carrega config corretamente
# ---------------------------------------------------------------------------
def test_script_loads_config():
    from src.edgehunter.runtime.orchestrator import _load_runtime_config
    cfg = _load_runtime_config({
        "EDGEHUNTER_RUNTIME_ENABLED": "false",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "2",
    })
    assert cfg["enabled"] is False
    assert cfg["dry_run"] is True
    assert cfg["max_cycles"] == 2


# ---------------------------------------------------------------------------
# 2. Runtime disabled por padrão (sem variáveis)
# ---------------------------------------------------------------------------
def test_runtime_disabled_by_default():
    from src.edgehunter.runtime.orchestrator import _load_runtime_config
    # Remove variáveis de ambiente para testar o padrão
    clean_env = {k: v for k, v in os.environ.items()
                 if not k.startswith("EDGEHUNTER_RUNTIME")}
    cfg = _load_runtime_config({
        "EDGEHUNTER_RUNTIME_ENABLED": "false"
    })
    assert cfg["enabled"] is False


# ---------------------------------------------------------------------------
# 3. max_cycles em teste evita loop
# ---------------------------------------------------------------------------
def test_max_cycles_prevents_loop():
    from src.edgehunter.runtime.orchestrator import run_runtime
    env = {
        "EDGEHUNTER_RUNTIME_ENABLED": "true",
        "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        "EDGEHUNTER_RUNTIME_MAX_CYCLES": "2",
        "EDGEHUNTER_RUNTIME_INTERVAL_SECONDS": "0",
    }
    summary = run_runtime(env=env)
    assert summary["cycles_executed"] == 2
    assert "max_cycles_reached" in summary["shutdown_reason"]


# ---------------------------------------------------------------------------
# 4. Sem rede real
# ---------------------------------------------------------------------------
def test_no_real_network():
    import socket
    calls = []
    original = socket.socket.connect
    def mock_connect(self, address):
        calls.append(address)
        return original(self, address)
    with patch.object(socket.socket, "connect", mock_connect):
        from src.edgehunter.runtime.orchestrator import run_runtime
        run_runtime(env={
            "EDGEHUNTER_RUNTIME_ENABLED": "false",
            "EDGEHUNTER_RUNTIME_DRY_RUN": "true",
        })
    assert calls == []


# ---------------------------------------------------------------------------
# 5. Sem shell perigoso no script
# ---------------------------------------------------------------------------
def test_no_dangerous_shell_in_run_runtime():
    import scripts.run_runtime as mod
    import inspect
    src_code = inspect.getsource(mod)
    for term in ["os.system(", "subprocess.call(", "subprocess.run(", "shell=True"]:
        assert term not in src_code, f"Shell perigoso encontrado: {term}"


# ---------------------------------------------------------------------------
# 6. Arquivo systemd não contém segredo real
# ---------------------------------------------------------------------------
def test_systemd_file_no_real_secret():
    service_file = "deploy/systemd/edgehunter.service.example"
    with open(service_file, encoding="utf-8") as f:
        content = f.read()
    for secret in ["password=", "api_key=", "bot_token=", "secret="]:
        lower = content.lower()
        # Verificar que não há segredo real (valor não vazio)
        import re
        matches = re.findall(rf"{secret}(\S+)", lower)
        for match in matches:
            assert match in ("", "your_", "YOUR_", "PLACEHOLDER"), \
                f"Possível segredo real em {service_file}: {secret}{match}"


# ---------------------------------------------------------------------------
# 7. README documenta flags
# ---------------------------------------------------------------------------
def test_readme_documents_flags():
    readme = "deploy/README_SERVER.md"
    with open(readme, encoding="utf-8") as f:
        content = f.read()
    for flag in ["GEMINI_ENABLED", "SCRAPER_ENABLED", "TELEGRAM_ENABLED",
                 "EDGEHUNTER_RUNTIME_ENABLED", "EDGEHUNTER_RUNTIME_DRY_RUN"]:
        assert flag in content, f"Flag não documentada no README: {flag}"


# ---------------------------------------------------------------------------
# 8. Sem execução financeira no run_runtime
# ---------------------------------------------------------------------------
def test_no_financial_execution_in_run_runtime():
    import scripts.run_runtime as mod
    import inspect
    src_code = inspect.getsource(mod)
    for pattern in ["execute_bet(", "place_bet(", "financial_exec(", "autoevolution("]:
        assert pattern not in src_code.lower(), f"Chamada proibida: {pattern}"
