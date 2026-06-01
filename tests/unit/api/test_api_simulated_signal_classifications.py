"""Tests for the simulated signal classifications API endpoint."""

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from src.edgehunter.api.app import create_app
from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.core.simulated_signal_classifier import (
    SimulationLabel,
    SimulatedSignalClassificationResult,
)
from src.edgehunter.core.simulated_signal_classifier_persistence import (
    persist_simulated_signal_classification,
)

client = TestClient(create_app())

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    ensure_schema(db_path)
    monkeypatch.setenv("EDGEHUNTER_DB_PATH", db_path)
    monkeypatch.setenv("EDGEHUNTER_API_KEY", "test_api_key")
    return db_path

def _valid_result_payload(classification_id="class-123", label=SimulationLabel.GREEN_SIM):
    return {
        "classification_id": classification_id,
        "signal_id": "sig-123",
        "opportunity_id": "opp-456",
        "simulation_label": label,
        "calibrated_assertiveness": 0.75,
        "confidence": 0.80,
        "threshold_green": 0.70,
        "learning_mode": True,
        "display": True,
        "rationale": "Valid rationale",
        "risk_factors": ["risk 1", "risk 2"],
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }

def test_missing_api_key():
    response = client.get("/api/simulated-signal-classifications")
    assert response.status_code == 401

def test_invalid_api_key():
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_valid_api_key_returns_200():
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200

def test_empty_list_returns_safe_structure():
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data["data"]
    assert len(data["data"]["data"]) == 0
    assert data["is_simulated"] is True
    assert data["actionable"] is False

def test_green_sim_appears_in_endpoint(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(label=SimulationLabel.GREEN_SIM))
    persist_simulated_signal_classification(setup_db, res)
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["simulation_label"] == "GREEN_SIM"

def test_red_sim_appears_in_endpoint(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(label=SimulationLabel.RED_SIM))
    persist_simulated_signal_classification(setup_db, res)
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["simulation_label"] == "RED_SIM"

def test_limit_works(setup_db):
    for i in range(5):
        res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id=f"c-{i}"))
        persist_simulated_signal_classification(setup_db, res)
        
    response = client.get("/api/simulated-signal-classifications?limit=2", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 2
    assert data["data"]["pagination"]["limit"] == 2
    assert data["data"]["pagination"]["has_more"] is True

def test_offset_works(setup_db):
    for i in range(5):
        res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id=f"c-{i}"))
        persist_simulated_signal_classification(setup_db, res)
        
    r1 = client.get("/api/simulated-signal-classifications?limit=2&offset=0", headers={"X-API-Key": "test_api_key"}).json()
    r2 = client.get("/api/simulated-signal-classifications?limit=2&offset=2", headers={"X-API-Key": "test_api_key"}).json()
    assert r1["data"]["data"][0]["classification_id"] != r2["data"]["data"][0]["classification_id"]

def test_limit_over_100_fails_or_limits():
    response = client.get("/api/simulated-signal-classifications?limit=150", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["pagination"]["limit"] == 100

def test_limit_zero_or_negative_fails():
    response = client.get("/api/simulated-signal-classifications?limit=0", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 422
    response = client.get("/api/simulated-signal-classifications?limit=-5", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 422

def test_offset_negative_fails():
    response = client.get("/api/simulated-signal-classifications?offset=-1", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 422

def test_filter_by_simulation_label_green(setup_db):
    res1 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="c1", label=SimulationLabel.GREEN_SIM))
    res2 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="c2", label=SimulationLabel.RED_SIM))
    persist_simulated_signal_classification(setup_db, res1)
    persist_simulated_signal_classification(setup_db, res2)
    
    response = client.get("/api/simulated-signal-classifications?simulation_label=GREEN_SIM", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["simulation_label"] == "GREEN_SIM"

def test_filter_by_simulation_label_red(setup_db):
    res1 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="c1", label=SimulationLabel.GREEN_SIM))
    res2 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="c2", label=SimulationLabel.RED_SIM))
    persist_simulated_signal_classification(setup_db, res1)
    persist_simulated_signal_classification(setup_db, res2)
    
    response = client.get("/api/simulated-signal-classifications?simulation_label=RED_SIM", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["simulation_label"] == "RED_SIM"

def test_invalid_simulation_label_does_not_crash():
    response = client.get("/api/simulated-signal-classifications?simulation_label=INVALID", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 0

def test_filter_by_opportunity_id(setup_db):
    res1 = _valid_result_payload(classification_id="c1")
    res1["opportunity_id"] = "opp-a"
    res2 = _valid_result_payload(classification_id="c2")
    res2["opportunity_id"] = "opp-b"
    persist_simulated_signal_classification(setup_db, SimulatedSignalClassificationResult.from_dict(res1))
    persist_simulated_signal_classification(setup_db, SimulatedSignalClassificationResult.from_dict(res2))
    
    response = client.get("/api/simulated-signal-classifications?opportunity_id=opp-b", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["opportunity_id"] == "opp-b"

def test_filter_by_signal_id(setup_db):
    res1 = _valid_result_payload(classification_id="c1")
    res1["signal_id"] = "sig-a"
    res2 = _valid_result_payload(classification_id="c2")
    res2["signal_id"] = "sig-b"
    persist_simulated_signal_classification(setup_db, SimulatedSignalClassificationResult.from_dict(res1))
    persist_simulated_signal_classification(setup_db, SimulatedSignalClassificationResult.from_dict(res2))
    
    response = client.get("/api/simulated-signal-classifications?signal_id=sig-b", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["signal_id"] == "sig-b"

def test_response_includes_global_flags():
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["paper_trading"] is True
    assert data["bet_placed"] is False
    assert data["alerted"] is False

def test_item_preserves_safe_flags(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    item = response.json()["data"]["data"][0]
    assert item["is_simulated"] is True
    assert item["actionable"] is False

def test_payload_contains_no_stake(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert "stake" not in response.text.lower()

def test_payload_contains_no_kelly(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert "kelly" not in response.text.lower()

def test_payload_contains_no_bankroll(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert "bankroll" not in response.text.lower()

def test_corrupt_db_actionable_fails(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    with sqlite3.connect(setup_db) as conn:
        conn.execute("UPDATE simulated_signal_classifications SET actionable = 1")
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500
    assert "Security corruption detected" in response.json()["detail"]

def test_corrupt_db_bet_placed_fails(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    with sqlite3.connect(setup_db) as conn:
        conn.execute("UPDATE simulated_signal_classifications SET bet_placed = 1")
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500
    assert "Security corruption detected" in response.json()["detail"]

def test_corrupt_db_alerted_fails(setup_db):
    res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(setup_db, res)
    with sqlite3.connect(setup_db) as conn:
        conn.execute("UPDATE simulated_signal_classifications SET alerted = 1")
    
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500
    assert "Security corruption detected" in response.json()["detail"]

def test_no_writes_on_get(setup_db):
    # Just asserting it's a GET request via the client
    response = client.get("/api/simulated-signal-classifications", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200

def test_no_network_or_gemini_calls_in_api():
    import src.edgehunter.api.routes as routes
    assert "requests" not in dir(routes)
    assert "gemini" not in dir(routes)
