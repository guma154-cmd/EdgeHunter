import pytest
import sqlite3
import json
import os
from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome, OutcomeStatus
from src.edgehunter.core.simulated_signal_outcome_persistence import persist_simulated_signal_outcome, list_simulated_signal_outcomes

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    ensure_schema(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

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


def test_schema_creates_table(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='simulated_signal_outcomes'")
        assert cursor.fetchone() is not None
    finally:
        conn.close()

def test_persist_positive_observed(db_path):
    outcome = _valid_outcome("POSITIVE_OBSERVED")
    pk = persist_simulated_signal_outcome(db_path, outcome)
    assert pk > 0

def test_persist_negative_observed(db_path):
    outcome = _valid_outcome("NEGATIVE_OBSERVED")
    pk = persist_simulated_signal_outcome(db_path, outcome)
    assert pk > 0

def test_persist_unresolved(db_path):
    outcome = _valid_outcome("UNRESOLVED")
    pk = persist_simulated_signal_outcome(db_path, outcome)
    assert pk > 0

def test_persist_invalidated(db_path):
    outcome = _valid_outcome("INVALIDATED")
    pk = persist_simulated_signal_outcome(db_path, outcome)
    assert pk > 0

def test_persist_idempotent(db_path):
    outcome = _valid_outcome()
    pk1 = persist_simulated_signal_outcome(db_path, outcome)
    pk2 = persist_simulated_signal_outcome(db_path, outcome)
    assert pk1 == pk2

def test_list_returns_outcome(db_path):
    outcome = _valid_outcome()
    persist_simulated_signal_outcome(db_path, outcome)
    
    result = list_simulated_signal_outcomes(db_path)
    assert len(result["data"]) == 1
    assert result["data"][0]["outcome_id"] == "out-123"
    assert result["data"][0]["is_simulated"] is True
    assert result["data"][0]["actionable"] is False

def test_filter_by_outcome_status(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome("POSITIVE_OBSERVED", outcome_id="o1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome("NEGATIVE_OBSERVED", outcome_id="o2"))
    
    res = list_simulated_signal_outcomes(db_path, outcome_status="POSITIVE_OBSERVED")
    assert len(res["data"]) == 1
    assert res["data"][0]["outcome_id"] == "o1"

def test_filter_by_signal_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", signal_id="s1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", signal_id="s2"))
    
    res = list_simulated_signal_outcomes(db_path, signal_id="s2")
    assert len(res["data"]) == 1
    assert res["data"][0]["outcome_id"] == "o2"

def test_filter_by_classification_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", classification_id="c1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", classification_id="c2"))
    
    res = list_simulated_signal_outcomes(db_path, classification_id="c1")
    assert len(res["data"]) == 1
    assert res["data"][0]["outcome_id"] == "o1"

def test_filter_by_opportunity_id(db_path):
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o1", opportunity_id="op1"))
    persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id="o2", opportunity_id="op2"))
    
    res = list_simulated_signal_outcomes(db_path, opportunity_id="op2")
    assert len(res["data"]) == 1
    assert res["data"][0]["outcome_id"] == "o2"

def test_pagination(db_path):
    for i in range(5):
        persist_simulated_signal_outcome(db_path, _valid_outcome(outcome_id=f"o{i}"))
        
    res = list_simulated_signal_outcomes(db_path, limit=2, offset=0)
    assert len(res["data"]) == 2
    assert res["pagination"]["count"] == 2
    assert res["pagination"]["has_more"] is True

def test_limit_max_100(db_path):
    res = list_simulated_signal_outcomes(db_path, limit=150)
    assert res["pagination"]["limit"] == 100

def test_limit_zero_fails(db_path):
    with pytest.raises(ValueError):
        list_simulated_signal_outcomes(db_path, limit=0)

def test_offset_negative_fails(db_path):
    with pytest.raises(ValueError):
        list_simulated_signal_outcomes(db_path, offset=-1)

def test_safety_flags_are_preserved(db_path):
    outcome = _valid_outcome()
    persist_simulated_signal_outcome(db_path, outcome)
    
    res = list_simulated_signal_outcomes(db_path)
    data = res["data"][0]
    
    assert data["is_simulated"] is True
    assert data["paper_trading"] is True
    assert data["learning_mode"] is True
    assert data["actionable"] is False
    assert data["bet_placed"] is False
    assert data["alerted"] is False
    assert data["not_operational_advice"] is True

def test_actionable_true_fails():
    with pytest.raises(ValueError):
        _valid_outcome(actionable=True)

def test_bet_placed_true_fails():
    with pytest.raises(ValueError):
        _valid_outcome(bet_placed=True)

def test_alerted_true_fails():
    with pytest.raises(ValueError):
        _valid_outcome(alerted=True)

def test_notes_operational_fails():
    with pytest.raises(ValueError):
        _valid_outcome(notes="ajustar stake")

def test_no_financial_fields(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("PRAGMA table_info(simulated_signal_outcomes)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "stake" not in columns
        assert "kelly" not in columns
        assert "bankroll" not in columns
    finally:
        conn.close()

def test_no_network_imports():
    with open("src/edgehunter/core/simulated_signal_outcome_persistence.py") as f:
        content = f.read()
    assert "requests" not in content
    assert "httpx" not in content

def test_no_gemini_imports():
    with open("src/edgehunter/core/simulated_signal_outcome_persistence.py") as f:
        content = f.read()
    assert "google" not in content
    assert "gemini" not in content

def test_no_telegram_scheduler():
    with open("src/edgehunter/core/simulated_signal_outcome_persistence.py") as f:
        content = f.read()
    assert "telegram" not in content.lower()
    assert "schedule" not in content.lower()

def test_no_auto_evolution():
    with open("src/edgehunter/core/simulated_signal_outcome_persistence.py") as f:
        content = f.read()
    assert "auto_evolution" not in content.lower()

def test_no_financial_execution():
    with open("src/edgehunter/core/simulated_signal_outcome_persistence.py") as f:
        content = f.read()
    assert "execute_bet" not in content.lower()
