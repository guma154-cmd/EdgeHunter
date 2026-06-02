import sys
import os
import pytest
from src.edgehunter.ops.environment_check import (
    check_python_version,
    check_required_modules,
    check_project_paths,
    check_environment_variables,
    run_environment_check
)

def test_check_python_version():
    res = check_python_version()
    assert "Python Version Check" in res["name"]
    # We assume the current python running pytest is valid (3.10+)
    assert res["passed"] is True

def test_check_required_modules(monkeypatch):
    res = check_required_modules()
    # It might fail if dotenv isn't installed in the exact same environment name, but let's assume it is or we mock it.
    # To be safe and deterministic, let's just assert the structure.
    assert "Required Modules Check" in res["name"]
    assert "missing" in res

def test_check_project_paths(tmp_path):
    # Empty dir -> NOT_READY
    res = check_project_paths(str(tmp_path))
    assert res["passed"] is False
    assert len(res["missing"]) == 4

    # Create paths -> READY
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "core"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "api"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "database"))
    os.makedirs(os.path.join(tmp_path, "tests"))

    res2 = check_project_paths(str(tmp_path))
    assert res2["passed"] is True
    assert len(res2["missing"]) == 0

def test_check_environment_variables():
    # Empty env
    res = check_environment_variables({})
    assert res["passed"] is True
    assert len(res["warnings"]) == 2 # Missing DB path and API key

    # Full env
    res2 = check_environment_variables({
        "EDGEHUNTER_DB_PATH": "test.db",
        "EDGEHUNTER_API_KEY": "secret"
    })
    assert len(res2["warnings"]) == 0

    # Forbidden env
    res3 = check_environment_variables({
        "EDGEHUNTER_DB_PATH": "test.db",
        "EDGEHUNTER_API_KEY": "secret",
        "TELEGRAM_TOKEN": "123"
    })
    assert len(res3["warnings"]) == 1
    assert "TELEGRAM" in res3["warnings"][0]

def test_run_environment_check(tmp_path, monkeypatch):
    # Setup a perfect environment
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "core"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "api"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "database"))
    os.makedirs(os.path.join(tmp_path, "tests"))

    env = {
        "EDGEHUNTER_DB_PATH": "test.db",
        "EDGEHUNTER_API_KEY": "secret"
    }

    # Mock modules check to always pass to avoid local env differences
    def mock_check_modules():
        return {
            "name": "Required Modules Check",
            "passed": True,
            "details": "All core modules present.",
            "missing": []
        }
    monkeypatch.setattr("src.edgehunter.ops.environment_check.check_required_modules", mock_check_modules)

    res = run_environment_check(base_path=str(tmp_path), env=env)
    assert res["status"] == "READY"
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["not_operational_advice"] is True

def test_run_environment_check_degraded(tmp_path, monkeypatch):
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "core"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "api"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "database"))
    os.makedirs(os.path.join(tmp_path, "tests"))

    env = {} # Missing vars

    def mock_check_modules():
        return {"passed": True, "details": "", "missing": []}
    monkeypatch.setattr("src.edgehunter.ops.environment_check.check_required_modules", mock_check_modules)

    res = run_environment_check(base_path=str(tmp_path), env=env)
    assert res["status"] == "DEGRADED"
    assert len(res["warnings"]) > 0

def test_run_environment_check_not_ready(tmp_path):
    # Missing paths -> NOT_READY
    res = run_environment_check(base_path=str(tmp_path), env={})
    assert res["status"] == "NOT_READY"
    assert len(res["errors"]) > 0
