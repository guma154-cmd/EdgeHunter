import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.edgehunter.api.app import create_app
from src.edgehunter.core.simulated_signal_classifier import (
    SimulatedSignalClassificationResult,
    SimulationLabel,
)
from src.edgehunter.core.simulated_signal_classifier_persistence import (
    persist_simulated_signal_classification,
)
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome
from src.edgehunter.core.simulated_signal_outcome_persistence import (
    persist_simulated_signal_outcome,
)
from src.edgehunter.database.schema import ensure_schema


client = TestClient(create_app())


@pytest.fixture(autouse=True)
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    ensure_schema(path)
    monkeypatch.setenv("EDGEHUNTER_DB_PATH", path)
    monkeypatch.setenv("EDGEHUNTER_API_KEY", "test_api_key")
    return path


def _classification(**overrides):
    payload = {
        "classification_id": "class-1",
        "signal_id": "sig-1",
        "opportunity_id": "opp-1",
        "simulation_label": SimulationLabel.GREEN_SIM,
        "calibrated_assertiveness": 0.8,
        "confidence": 0.7,
        "threshold_green": 0.7,
        "learning_mode": True,
        "display": True,
        "rationale": "Classificacao tecnica simulada",
        "risk_factors": ["Amostra tecnica limitada"],
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return SimulatedSignalClassificationResult(**payload)


def _outcome(**overrides):
    payload = {
        "outcome_id": "out-1",
        "signal_id": "sig-1",
        "classification_id": "class-1",
        "opportunity_id": "opp-1",
        "outcome_status": "POSITIVE_OBSERVED",
        "observed_at": "2026-06-01T12:00:00Z",
        "source": "manual_review",
        "notes": "technical review only",
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return SimulatedSignalOutcome.from_dict(payload)


def _url():
    return (
        "/api/dashboard/evolution-report"
        "?period=daily"
        "&current_period_start=2000-01-01T00:00:00Z"
        "&current_period_end=2100-01-01T00:00:00Z"
    )


def _counts(db_path):
    with sqlite3.connect(db_path) as conn:
        return (
            conn.execute("SELECT COUNT(*) FROM simulated_signal_classifications").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM simulated_signal_outcomes").fetchone()[0],
        )


def test_without_api_key_fails():
    response = client.get(_url())
    assert response.status_code == 401


def test_wrong_api_key_fails():
    response = client.get(_url(), headers={"X-API-Key": "wrong"})
    assert response.status_code == 403


def test_correct_api_key_returns_report(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())

    response = client.get(_url(), headers={"X-API-Key": "test_api_key"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"]["period"] == "daily"
    assert payload["data"]["green_confirmed"] == 1
    assert payload["is_simulated"] is True
    assert payload["actionable"] is False


def test_endpoint_does_not_write_to_database(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())
    before = _counts(db_path)

    client.get(_url(), headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path) == before


def test_invalid_period_fails():
    response = client.get(
        _url().replace("period=daily", "period=yearly"),
        headers={"X-API-Key": "test_api_key"},
    )
    assert response.status_code == 400


def test_only_get_exists():
    assert client.post(_url(), headers={"X-API-Key": "test_api_key"}).status_code == 405
