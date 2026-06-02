import pytest
from datetime import datetime
import json
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome, OutcomeStatus

def _valid_payload(**kwargs):
    payload = {
        "outcome_id": "out-123",
        "signal_id": "sig-123",
        "classification_id": "class-123",
        "opportunity_id": "opp-123",
        "outcome_status": "POSITIVE_OBSERVED",
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
    return payload

def test_creates_outcome_status_valid():
    assert OutcomeStatus.POSITIVE_OBSERVED.value == "POSITIVE_OBSERVED"

def test_creates_valid_positive_observed():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload(outcome_status="POSITIVE_OBSERVED"))
    assert outcome.outcome_status == OutcomeStatus.POSITIVE_OBSERVED

def test_creates_valid_negative_observed():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload(outcome_status="NEGATIVE_OBSERVED"))
    assert outcome.outcome_status == OutcomeStatus.NEGATIVE_OBSERVED

def test_creates_valid_unresolved():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload(outcome_status="UNRESOLVED"))
    assert outcome.outcome_status == OutcomeStatus.UNRESOLVED

def test_creates_valid_invalidated():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload(outcome_status="INVALIDATED"))
    assert outcome.outcome_status == OutcomeStatus.INVALIDATED

def test_outcome_status_invalid_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(outcome_status="INVALID_STATUS"))

def test_outcome_id_empty_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(outcome_id=""))

def test_signal_id_empty_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(signal_id=""))

def test_classification_id_empty_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(classification_id=""))

def test_opportunity_id_empty_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(opportunity_id=""))

def test_source_empty_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(source=""))

def test_observed_at_invalid_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(observed_at="invalid-date"))

def test_actionable_true_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(actionable=True))

def test_bet_placed_true_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(bet_placed=True))

def test_alerted_true_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(alerted=True))

def test_is_simulated_false_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(is_simulated=False))

def test_paper_trading_false_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(paper_trading=False))

def test_learning_mode_false_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(learning_mode=False))

def test_not_operational_advice_false_fails():
    with pytest.raises(ValueError):
        SimulatedSignalOutcome.from_dict(_valid_payload(not_operational_advice=False))

def test_notes_with_operational_language_fails():
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalOutcome.from_dict(_valid_payload(notes="deu lucro"))
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalOutcome.from_dict(_valid_payload(notes="green na operacao"))

def test_stake_field_fails():
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(stake=10))

def test_kelly_field_fails():
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(kelly=0.05))

def test_bankroll_field_fails():
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(bankroll=100))

def test_lucro_gain_field_fails():
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(lucro=10))
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(gain=10))

def test_execute_execution_field_fails():
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(execute=True))
    with pytest.raises(ValueError, match="forbidden field"):
        SimulatedSignalOutcome.from_dict(_valid_payload(execution="started"))

def test_to_dict_is_deterministic():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload())
    d1 = outcome.to_dict()
    d2 = outcome.to_dict()
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)

def test_security_flags_are_preserved():
    outcome = SimulatedSignalOutcome.from_dict(_valid_payload())
    assert outcome.is_simulated is True
    assert outcome.actionable is False
    assert outcome.bet_placed is False

def test_no_network_imports():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content

def test_no_gemini_imports():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "google" not in content
    assert "gemini" not in content

def test_no_telegram():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "telegram" not in content.lower()

def test_no_scheduler():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "scheduler" not in content.lower()

def test_no_auto_evolution():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "autoevolution" not in content.lower()

def test_no_persistence():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "sqlite" not in content.lower()
    assert "db" not in content.lower()
    assert "insert" not in content.lower()

def test_no_api():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "fastapi" not in content.lower()
    assert "flask" not in content.lower()

def test_no_real_bet_or_financial_execution():
    with open("src/edgehunter/core/simulated_signal_outcome.py") as f:
        content = f.read()
    assert "requests" not in content.lower()
    assert "real_bet" not in content.lower()
