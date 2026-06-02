import sqlite3

import pytest
from fastapi.testclient import TestClient

import src.edgehunter.api.routes as routes
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
        return (
            conn.execute("SELECT COUNT(*) FROM simulated_signal_classifications").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM simulated_signal_outcomes").fetchone()[0],
        )


def test_api_without_key_fails():
    assert client.get("/api/dashboard/summary").status_code == 401


def test_api_invalid_key_fails():
    assert client.get("/api/dashboard/summary", headers={"X-API-Key": "bad"}).status_code == 403


def test_corrupted_actionable_payload_fails(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE simulated_signal_classifications SET actionable = 1")
        conn.commit()

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 500


def test_corrupted_bet_placed_payload_fails(db_path):
    persist_simulated_signal_outcome(db_path, _outcome())
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE simulated_signal_outcomes SET bet_placed = 1")
        conn.commit()

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 500


def test_payload_with_stake_fails(monkeypatch):
    monkeypatch.setattr(routes, "_read_dashboard_inputs", lambda **kwargs: ([{"stake": 1}], []))

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 400


def test_payload_with_kelly_fails(monkeypatch):
    monkeypatch.setattr(routes, "_read_dashboard_inputs", lambda **kwargs: ([{"kelly": 0.1}], []))

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 400


def test_payload_with_bankroll_fails(monkeypatch):
    monkeypatch.setattr(routes, "_read_dashboard_inputs", lambda **kwargs: ([{"bankroll": 100}], []))

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 400


def test_payload_with_operational_language_fails(monkeypatch):
    monkeypatch.setattr(
        routes,
        "_read_dashboard_inputs",
        lambda **kwargs: ([{"classification_id": "class-1", "rationale": "ajustar stake"}], []),
    )

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 400


def test_endpoint_does_not_write_to_database(db_path):
    persist_simulated_signal_classification(db_path, _classification())
    persist_simulated_signal_outcome(db_path, _outcome())
    before = _counts(db_path)

    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.status_code == 200
    assert _counts(db_path) == before


def test_endpoint_does_not_alter_threshold(db_path):
    response = client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert response.json()["data"]["current_threshold"] == 0.7


def test_endpoint_does_not_create_outcome(db_path):
    before = _counts(db_path)

    client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path)[1] == before[1]


def test_endpoint_does_not_create_classification(db_path):
    before = _counts(db_path)

    client.get("/api/dashboard/summary", headers={"X-API-Key": "test_api_key"})

    assert _counts(db_path)[0] == before[0]


def test_route_does_not_call_network():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests." not in content
    assert "httpx." not in content


def test_route_does_not_call_external_ai_provider():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "google.generative" not in content
    assert "genai" not in content


def test_route_does_not_call_notification_or_timer_runtime():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_route_does_not_call_auto_evolution_runtime():
    with open("src/edgehunter/api/routes.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "autoevolution" not in content
    assert "auto_evolution" not in content


def test_openapi_has_no_new_operational_language():
    openapi_text = str(client.get("/openapi.json").json()).lower()

    assert "place_bet" not in openapi_text
    assert "execute_bet" not in openapi_text


def test_openapi_documents_dashboard_endpoints_as_read_only():
    openapi = client.get("/openapi.json").json()

    assert set(openapi["paths"]["/api/dashboard/summary"].keys()) == {"get"}
    assert set(openapi["paths"]["/api/calibration/summary"].keys()) == {"get"}
