import os
import pytest
from scripts.clean_install_check import run_clean_install_check


def _make_minimal_project(tmp_path):
    """Cria estrutura mínima válida de projeto para testes."""
    import sqlite3

    required_files = [
        "pyproject.toml",
        ".env.example",
        "docs/OPERATIONS_MANUAL.md",
        "docs/LOCAL_DEPLOYMENT.md",
        "docs/BACKUP_RESTORE.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/RELEASE_HISTORY.md",
        "docs/PROJECT_STATUS.md",
        "scripts/run_local_api.py",
        "scripts/smoke_test_local.py",
        "scripts/release_check.py",
        "src/edgehunter/api/app.py",
        "src/edgehunter/api/routes.py",
        "src/edgehunter/ops/backup_restore.py",
        "src/edgehunter/ops/environment_check.py",
        "src/edgehunter/ops/config.py",
    ]
    for rel in required_files:
        fp = tmp_path / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("# placeholder")

    # Add a test file so tests_listable passes
    test_file = tmp_path / "tests" / "unit" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_pass(): pass")

    return tmp_path


def test_valid_project_returns_ready(monkeypatch):
    """Projeto real retorna READY (sem imports falhando)."""
    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    res = run_clean_install_check(project_root=base_path)
    assert res["status"] == "READY", f"Errors: {res['errors']}"
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True
    assert res["is_simulated"] is True


def test_missing_pyproject_returns_not_ready(tmp_path, monkeypatch):
    """Ausência de pyproject.toml retorna NOT_READY."""
    _make_minimal_project(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.unlink()

    # Patch imports so they don't fail (we just want to test file checks)
    monkeypatch.setattr("scripts.clean_install_check.REQUIRED_IMPORTS", [])

    res = run_clean_install_check(project_root=str(tmp_path))
    assert res["status"] == "NOT_READY"
    assert any("pyproject.toml" in e for e in res["errors"])


def test_missing_env_example_returns_not_ready(tmp_path, monkeypatch):
    """Ausência de .env.example retorna NOT_READY."""
    _make_minimal_project(tmp_path)
    env_example = tmp_path / ".env.example"
    env_example.unlink()

    monkeypatch.setattr("scripts.clean_install_check.REQUIRED_IMPORTS", [])

    res = run_clean_install_check(project_root=str(tmp_path))
    assert res["status"] == "NOT_READY"
    assert any(".env.example" in e for e in res["errors"])


def test_missing_docs_returns_not_ready(tmp_path, monkeypatch):
    """Ausência de doc principal retorna NOT_READY."""
    _make_minimal_project(tmp_path)
    ops_manual = tmp_path / "docs" / "OPERATIONS_MANUAL.md"
    ops_manual.unlink()

    monkeypatch.setattr("scripts.clean_install_check.REQUIRED_IMPORTS", [])

    res = run_clean_install_check(project_root=str(tmp_path))
    assert res["status"] == "NOT_READY"
    assert any("OPERATIONS_MANUAL.md" in e for e in res["errors"])


def test_missing_scripts_returns_not_ready(tmp_path, monkeypatch):
    """Ausência de script principal retorna NOT_READY."""
    _make_minimal_project(tmp_path)
    smoke = tmp_path / "scripts" / "smoke_test_local.py"
    smoke.unlink()

    monkeypatch.setattr("scripts.clean_install_check.REQUIRED_IMPORTS", [])

    res = run_clean_install_check(project_root=str(tmp_path))
    assert res["status"] == "NOT_READY"
    assert any("smoke_test_local.py" in e for e in res["errors"])


def test_result_is_deterministic():
    """Resultado é determinístico entre chamadas."""
    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    res1 = run_clean_install_check(project_root=base_path)
    res2 = run_clean_install_check(project_root=base_path)
    assert res1["status"] == res2["status"]
    assert len(res1["checks"]) == len(res2["checks"])


def test_does_not_call_network(monkeypatch):
    """Não chama rede: socket.connect está disponível, mas não é invocado."""
    import socket
    calls = []
    original_connect = socket.socket.connect

    def mock_connect(self, address):
        calls.append(address)
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", mock_connect)

    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    run_clean_install_check(project_root=base_path)
    assert calls == [], f"Network calls detected: {calls}"


def test_does_not_install_packages(monkeypatch):
    """Não instala pacotes: subprocess.run e pip não são invocados."""
    import subprocess
    calls = []

    def mock_run(*args, **kwargs):
        calls.append(args)
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(subprocess, "run", mock_run)

    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    run_clean_install_check(project_root=base_path)
    assert calls == []


def test_does_not_execute_shell(monkeypatch):
    """Não executa shell: os.system não é invocado."""
    calls = []

    def mock_system(cmd):
        calls.append(cmd)
        raise AssertionError("os.system should not be called")

    monkeypatch.setattr(os, "system", mock_system)

    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    run_clean_install_check(project_root=base_path)
    assert calls == []


def test_safe_flags_present():
    """Flags de segurança estão sempre presentes no resultado."""
    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    res = run_clean_install_check(project_root=base_path)
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True


def test_checks_list_not_empty():
    """Lista de checks nunca é vazia."""
    base_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    res = run_clean_install_check(project_root=base_path)
    assert len(res["checks"]) > 0
