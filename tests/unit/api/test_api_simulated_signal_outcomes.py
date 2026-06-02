import pytest
import sqlite3
import os
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app
from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome, OutcomeStatus
from src.edgehunter.core.simulated_signal_outcome_persistence import persist_simulated_signal_outcome

client = TestClient(create_app())

@pytest.fixture(autouse=True)
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    ensure_schema(path)
    monkeypatch.setenv("EDGEHUNTER_DB_PATH", path)
    monkeypatch.setenv("EDGEHUNTER_API_KEY", "test_api_key")
    return path
        
def _valid_outcome(status="POSITIVE_OBSERVED", **kwargs):
    payload = {
        "outcome_id": "out-123",
        "signal_id": "sig-123",
        "classification_id": "class-123",
        "opportunity_id": "opp-123",
        "outcome_status": status,
        "observed_at": "2024-01-01T12:00:00Z",
        "source": "manual_review",
        "notes": "market matched thesis",
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(kwargs)
    return SimulatedSignalOutcome.from_dict(payload)


def test_without_api_key_fails():
    response = client.get("/api/simulated-signal-outcomes")
    assert response.status_code == 401

def test_wrong_api_key_fails():
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_correct_api_key_empty_returns_200(db_path):
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["data"] == []
    assert data["is_simulated"] is True
    assert data["actionable"] is False

def test_persisted_outcome_appears(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    assert data["data"]["data"][0]["outcome_id"] == "out-123"
    assert data["is_simulated"] is True

def test_limit_works(db_path):
    for i in range(5):
        persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id=f"o{i}"))
        
    response = client.get("/api/simulated-signal-outcomes?limit=2", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 2

def test_offset_works(db_path):
    for i in range(5):
        persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id=f"o{i}"))
        
    response = client.get("/api/simulated-signal-outcomes?limit=2&offset=2", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 2

def test_limit_gt_100_limited(db_path):
    response = client.get("/api/simulated-signal-outcomes?limit=150", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert response.json()["data"]["pagination"]["limit"] == 100

def test_limit_zero_fails(db_path):
    response = client.get("/api/simulated-signal-outcomes?limit=0", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 422

def test_offset_negative_fails(db_path):
    response = client.get("/api/simulated-signal-outcomes?offset=-1", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 422

def test_filter_by_outcome_status(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome("POSITIVE_OBSERVED", outcome_id="o1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome("NEGATIVE_OBSERVED", outcome_id="o2"))
    
    response = client.get("/api/simulated-signal-outcomes?outcome_status=POSITIVE_OBSERVED", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 1
    assert response.json()["data"]["data"][0]["outcome_id"] == "o1"

def test_filter_by_signal_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", signal_id="s1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", signal_id="s2"))
    
    response = client.get("/api/simulated-signal-outcomes?signal_id=s2", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 1
    assert response.json()["data"]["data"][0]["outcome_id"] == "o2"

def test_filter_by_classification_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", classification_id="c1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", classification_id="c2"))
    
    response = client.get("/api/simulated-signal-outcomes?classification_id=c1", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 1
    assert response.json()["data"]["data"][0]["outcome_id"] == "o1"

def test_filter_by_opportunity_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", opportunity_id="op1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", opportunity_id="op2"))
    
    response = client.get("/api/simulated-signal-outcomes?opportunity_id=op2", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 1
    assert response.json()["data"]["data"][0]["outcome_id"] == "o2"

def test_response_includes_global_flags(db_path):
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    data = response.json()
    assert data["is_simulated"] is True
    assert data["paper_trading"] is True
    assert data["actionable"] is False
    assert data["bet_placed"] is False

def test_item_preserves_safe_flags(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    item = response.json()["data"]["data"][0]
    assert item["is_simulated"] is True
    assert item["paper_trading"] is True
    assert item["learning_mode"] is True
    assert item["actionable"] is False
    assert item["bet_placed"] is False
    assert item["alerted"] is False
    assert item["not_operational_advice"] is True

def test_no_financial_fields_in_payload(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    item = response.json()["data"]["data"][0]
    assert "stake" not in item
    assert "kelly" not in item
    assert "bankroll" not in item
    assert "bet_amount" not in item

def test_database_corrupted_actionable_fails(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE simulated_signal_outcomes SET actionable = 1")
        conn.commit()
    finally:
        conn.close()
    
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500

def test_database_corrupted_bet_placed_fails(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE simulated_signal_outcomes SET bet_placed = 1")
        conn.commit()
    finally:
        conn.close()
    
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500

def test_database_corrupted_alerted_fails(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE simulated_signal_outcomes SET alerted = 1")
        conn.commit()
    finally:
        conn.close()
    
    response = client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    assert response.status_code == 500

def test_does_not_write_during_get(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome())
    mtime1 = os.path.getmtime(db_path)
    client.get("/api/simulated-signal-outcomes", headers={"X-API-Key": "test_api_key"})
    mtime2 = os.path.getmtime(db_path)
    assert mtime1 == mtime2

def test_no_network_gemini_telegram_scheduler(db_path):
    with open("src/edgehunter/api/routes.py") as f:
        content = f.read()
    assert "requests" not in content
    assert "google" not in content
    assert "telegram" not in content.lower()
    assert "schedule" not in content.lower()
    assert "execute_bet" not in content.lower()
