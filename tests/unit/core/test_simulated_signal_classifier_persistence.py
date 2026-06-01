"""Unit tests for the simulated signal classifier persistence."""

import os
import pytest
import sqlite3

from src.edgehunter.core.simulated_signal_classifier import (
    SimulationLabel,
    SimulatedSignalClassificationResult,
)
from src.edgehunter.core.simulated_signal_classifier_persistence import (
    persist_simulated_signal_classification,
    list_simulated_signal_classifications,
)
from src.edgehunter.database.schema import ensure_schema

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    ensure_schema(str(path))
    return str(path)

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

def test_schema_creates_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='simulated_signal_classifications'")
    assert cursor.fetchone() is not None
    conn.close()

def test_persist_green_sim_valid(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(label=SimulationLabel.GREEN_SIM))
    row_id = persist_simulated_signal_classification(db_path, result)
    assert row_id > 0

def test_persist_red_sim_valid(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="class-red", label=SimulationLabel.RED_SIM))
    row_id = persist_simulated_signal_classification(db_path, result)
    assert row_id > 0

def test_persist_is_idempotent(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    id1 = persist_simulated_signal_classification(db_path, result)
    id2 = persist_simulated_signal_classification(db_path, result)
    assert id1 == id2
    
    rows = list_simulated_signal_classifications(db_path)["data"]
    assert len(rows) == 1

def test_read_returns_persisted_classification(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(db_path, result)
    
    rows = list_simulated_signal_classifications(db_path)["data"]
    assert len(rows) == 1
    assert rows[0]["classification_id"] == "class-123"

def test_filter_by_simulation_label(db_path):
    res1 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="class-g", label=SimulationLabel.GREEN_SIM))
    res2 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id="class-r", label=SimulationLabel.RED_SIM))
    persist_simulated_signal_classification(db_path, res1)
    persist_simulated_signal_classification(db_path, res2)
    
    green_rows = list_simulated_signal_classifications(db_path, simulation_label="GREEN_SIM")["data"]
    assert len(green_rows) == 1
    assert green_rows[0]["classification_id"] == "class-g"

def test_filter_by_opportunity_id(db_path):
    payload1 = _valid_result_payload(classification_id="c1")
    payload1["opportunity_id"] = "opp-1"
    payload2 = _valid_result_payload(classification_id="c2")
    payload2["opportunity_id"] = "opp-2"
    
    persist_simulated_signal_classification(db_path, SimulatedSignalClassificationResult.from_dict(payload1))
    persist_simulated_signal_classification(db_path, SimulatedSignalClassificationResult.from_dict(payload2))
    
    rows = list_simulated_signal_classifications(db_path, opportunity_id="opp-2")["data"]
    assert len(rows) == 1
    assert rows[0]["opportunity_id"] == "opp-2"

def test_filter_by_signal_id(db_path):
    payload1 = _valid_result_payload(classification_id="c1")
    payload1["signal_id"] = "sig-1"
    payload2 = _valid_result_payload(classification_id="c2")
    payload2["signal_id"] = "sig-2"
    
    persist_simulated_signal_classification(db_path, SimulatedSignalClassificationResult.from_dict(payload1))
    persist_simulated_signal_classification(db_path, SimulatedSignalClassificationResult.from_dict(payload2))
    
    rows = list_simulated_signal_classifications(db_path, signal_id="sig-2")["data"]
    assert len(rows) == 1
    assert rows[0]["signal_id"] == "sig-2"

def test_pagination_works(db_path):
    for i in range(10):
        res = SimulatedSignalClassificationResult.from_dict(_valid_result_payload(classification_id=f"c-{i}"))
        persist_simulated_signal_classification(db_path, res)
        
    rows = list_simulated_signal_classifications(db_path, limit=3, offset=0)["data"]
    assert len(rows) == 3
    # ordered by id desc, so latest first
    rows2 = list_simulated_signal_classifications(db_path, limit=3, offset=3)["data"]
    assert len(rows2) == 3
    assert rows[0]["id"] != rows2[0]["id"]

def test_risk_factors_is_serialized_as_json(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(db_path, result)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT risk_factors_json FROM simulated_signal_classifications")
    raw_json = cursor.fetchone()[0]
    conn.close()
    
    assert raw_json == '["risk 1", "risk 2"]'
    
    rows = list_simulated_signal_classifications(db_path)["data"]
    assert rows[0]["risk_factors"] == ["risk 1", "risk 2"]

def test_security_flags_are_preserved(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(db_path, result)
    
    rows = list_simulated_signal_classifications(db_path)["data"]
    r = rows[0]
    assert r["is_simulated"] is True
    assert r["paper_trading"] is True
    assert r["actionable"] is False
    assert r["bet_placed"] is False
    assert r["alerted"] is False
    assert r["not_operational_advice"] is True

def test_actionable_true_fails(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    object.__setattr__(result, "actionable", True)
    with pytest.raises(ValueError, match="actionable must be False"):
        persist_simulated_signal_classification(db_path, result)

def test_bet_placed_true_fails(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    object.__setattr__(result, "bet_placed", True)
    with pytest.raises(ValueError, match="bet_placed must be False"):
        persist_simulated_signal_classification(db_path, result)

def test_alerted_true_fails(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    object.__setattr__(result, "alerted", True)
    with pytest.raises(ValueError, match="alerted must be False"):
        persist_simulated_signal_classification(db_path, result)

def test_operational_rationale_fails(db_path):
    payload = _valid_result_payload()
    payload["rationale"] = "ajustar stake e place bet"
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_operational_risk_factors_fails(db_path):
    payload = _valid_result_payload()
    payload["risk_factors"] = ["Kelly ratio"]
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_does_not_record_financial_fields(db_path):
    result = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    persist_simulated_signal_classification(db_path, result)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(simulated_signal_classifications)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    assert "stake" not in columns
    assert "kelly" not in columns
    assert "bankroll" not in columns

def test_no_external_imports_in_persistence():
    import src.edgehunter.core.simulated_signal_classifier_persistence as mod
    import_names = dir(mod)
    assert "requests" not in import_names
    assert "google" not in import_names
    assert "gemini" not in import_names
    assert "telegram" not in import_names
    assert "schedule" not in import_names
