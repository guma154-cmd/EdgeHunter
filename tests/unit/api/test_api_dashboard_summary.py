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


def _outcome(status="POSITIVE_OBSERVED", **overrides):
    payload = {
        "outcome_id": "out-1",
        "signal_id": "sig-1",
        "classification_id": "class-1",
        "opportunity_id": "opp-1",
        "outcome_status": status,
        "observed_at": "2026-01-01T00:00:00Z",
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


def _counts(db_path):
    with sqlite3.connect(db_path) as conn:
        classifications = conn.execute(
            "SELECT COUNT(*) FROM simulated_signal_classifications"
        ).fetchone()[0]
        outcomes = conn.execute("SELECT COUNT(*) FROM simulated_signal_outcomes").fetchone()[0]
    return classifications, outcomes


def test_dashboard_without_api_key_fails():
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 401


def test_dashboard_wrong_api_key_fails():
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403


def test_dashboard_correct_api_key_returns_200(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 200


def test_dashboard_summary_returns_safe_structure(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload = response.json()

    assert payload["data"]["total_classifications"] == 1
    assert payload["data"]["total_outcomes"] == 1
    assert payload["data"]["green_confirmation_rate"] == 1.0
    assert payload["is_simulated"] is True
    assert payload["actionable"] is False


def test_calibration_summary_returns_safe_structure(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())

    response = client.get(
        "/api/calibration/summary?threshold_green=0.70&minimum_sample_size=1",
        headers={"X-API-Key": "test_api_key"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"]["calibration_report"]["matched_total"] == 1
    assert payload["data"]["threshold_suggestion"]["auto_apply"] is False
    assert payload["is_simulated"] is True


def test_payload_includes_global_safe_flags(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload = response.json()

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["learning_mode"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False
    assert payload["not_operational_advice"] is True


def test_payload_does_not_include_stake(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload_text = str(response.json()).lower()

    assert "stake" not in payload_text


def test_payload_does_not_include_kelly(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload_text = str(response.json()).lower()

    assert "kelly" not in payload_text


def test_payload_does_not_include_bankroll(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload_text = str(response.json()).lower()

    assert "bankroll" not in payload_text


def test_payload_does_not_include_operational_language(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})
    payload_text = str(response.json()).lower()

    assert "place_bet" not in payload_text
    assert "execute_bet" not in payload_text


def test_dashboard_endpoint_does_not_write_to_database(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())
    before = _counts(db_path)

    client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path) == before


def test_dashboard_endpoint_does_not_alter_threshold(db_path):
    response = client.get(
        "/api/dashboard/summary",
        headers={"X-API-Key": "test_api_key"},
    )

    assert response.json()["data"]["current_threshold"] == 0.7


def test_route_does_not_call_external_ai_provider():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "google.generative" not in content
    assert "genai" not in content


def test_route_does_not_call_network():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests." not in content
    assert "httpx." not in content


def test_dashboard_endpoint_does_not_create_classification(db_path):
    before = _counts(db_path)

    client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path)[0] == before[0]


def test_dashboard_endpoint_does_not_create_outcome(db_path):
    before = _counts(db_path)

    client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path)[1] == before[1]


def test_only_get_exists_for_dashboard_routes():
    assert client.post("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"}).status_code == 405
    assert client.put("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"}).status_code == 405
    assert client.patch("/api/calibration/summary", headers={"X-API-Key": "test_api_key"}).status_code == 405
    assert client.delete("/api/calibration/summary", headers={"X-API-Key": "test_api_key"}).status_code == 405
