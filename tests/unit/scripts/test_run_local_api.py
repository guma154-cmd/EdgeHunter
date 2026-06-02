import pytest
import os
from scripts.run_local_api import check_and_prepare_local_api

def test_check_and_prepare_local_api_valid(monkeypatch, tmp_path):
    # Mock environment check to pass
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "core"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "api"))
    os.makedirs(os.path.join(tmp_path, "src", "edgehunter", "database"))
    os.makedirs(os.path.join(tmp_path, "tests"))
    
    def mock_env_check(base_path, env):
        return {"status": "READY"}
    monkeypatch.setattr("scripts.run_local_api.run_environment_check", mock_env_check)
    
    env = {
        "EDGEHUNTER_API_KEY": "test",
        "EDGEHUNTER_READ_ONLY_MODE": "true",
        "EDGEHUNTER_IS_SIMULATED": "true",
        "EDGEHUNTER_PAPER_TRADING": "true",
        "EDGEHUNTER_ACTIONABLE": "false"
    }
    config = check_and_prepare_local_api(env_dict=env)
    assert config["api_key"] == "test"
    assert config["port"] == 8000

def test_check_and_prepare_local_api_invalid_config():
    env = {
        "EDGEHUNTER_READ_ONLY_MODE": "false"
    }
    with pytest.raises(ValueError, match="EDGEHUNTER_READ_ONLY_MODE"):
        check_and_prepare_local_api(env_dict=env)

def test_check_and_prepare_local_api_not_ready_env(monkeypatch):
    def mock_env_check(base_path, env):
        return {"status": "NOT_READY", "errors": ["Missing path"]}
    monkeypatch.setattr("scripts.run_local_api.run_environment_check", mock_env_check)
    
    env = {
        "EDGEHUNTER_READ_ONLY_MODE": "true",
        "EDGEHUNTER_IS_SIMULATED": "true",
        "EDGEHUNTER_PAPER_TRADING": "true",
        "EDGEHUNTER_ACTIONABLE": "false"
    }
    with pytest.raises(RuntimeError, match="NOT_READY"):
        check_and_prepare_local_api(env_dict=env)
