import pytest
import os
from src.edgehunter.ops.config import load_local_config, validate_local_config

def test_load_config_valid():
    env = {
        "EDGEHUNTER_API_KEY": "test-key",
        "EDGEHUNTER_PORT": "9000",
        "EDGEHUNTER_ACTIONABLE": "false"
    }
    cfg = load_local_config(env)
    assert cfg["api_key"] == "test-key"
    assert cfg["port"] == 9000
    assert cfg["read_only_mode"] is True
    assert cfg["is_simulated"] is True
    assert cfg["actionable"] is False

def test_apply_safe_defaults():
    cfg = load_local_config({})
    assert cfg["port"] == 8000
    assert cfg["host"] == "127.0.0.1"
    assert cfg["read_only_mode"] is True

def test_api_key_missing():
    cfg = load_local_config({})
    res = validate_local_config(cfg)
    assert res["status"] == "DEGRADED"

def test_invalid_port():
    cfg = load_local_config({"EDGEHUNTER_PORT": "99999"})
    with pytest.raises(ValueError, match="EDGEHUNTER_PORT"):
        validate_local_config(cfg)

def test_invalid_host():
    cfg = load_local_config({"EDGEHUNTER_HOST": "   "})
    with pytest.raises(ValueError, match="EDGEHUNTER_HOST"):
        validate_local_config(cfg)

def test_read_only_false():
    cfg = load_local_config({"EDGEHUNTER_READ_ONLY_MODE": "false"})
    with pytest.raises(ValueError, match="EDGEHUNTER_READ_ONLY_MODE"):
        validate_local_config(cfg)

def test_actionable_true():
    cfg = load_local_config({"EDGEHUNTER_ACTIONABLE": "true"})
    with pytest.raises(ValueError, match="EDGEHUNTER_ACTIONABLE"):
        validate_local_config(cfg)

def test_simulated_false():
    cfg = load_local_config({"EDGEHUNTER_IS_SIMULATED": "false"})
    with pytest.raises(ValueError, match="EDGEHUNTER_IS_SIMULATED"):
        validate_local_config(cfg)

def test_paper_trading_false():
    cfg = load_local_config({"EDGEHUNTER_PAPER_TRADING": "false"})
    with pytest.raises(ValueError, match="EDGEHUNTER_PAPER_TRADING"):
        validate_local_config(cfg)

def test_env_example_clean():
    # test that .env.example doesn't have real secrets or forbidden things
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env.example")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "TELEGRAM" not in content.upper()
    assert "GEMINI" not in content.upper()
    assert "YOUR_REAL_KEY" not in content
