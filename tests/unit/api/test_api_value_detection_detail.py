import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app
from src.edgehunter.database.schema import ensure_schema

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_edge_hunter.db")
    ensure_schema(db_path)
    os.environ["EDGEHUNTER_DB_PATH"] = db_path
    yield db_path
    if "EDGEHUNTER_DB_PATH" in os.environ:
        del os.environ["EDGEHUNTER_DB_PATH"]

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def auth_headers():
    os.environ["EDGEHUNTER_API_KEY"] = "secret"
    yield {"X-API-Key": "secret"}
    if "EDGEHUNTER_API_KEY" in os.environ:
        del os.environ["EDGEHUNTER_API_KEY"]

def insert_detection(db_path, **kwargs):
    default = {
        "opportunity_id": "opt1",
        "match_id": "match1",
        "market": "1x2",
        "selection": "home",
        "true_probability": 0.5,
        "offered_odds": 2.1,
        "expected_value": 0.05,
        "edge_percentage": 5.0,
        "source": "consensus",
        "detection_method": "method1",
        "created_at": "2026-05-31T00:00:00Z",
        "is_simulated": 1,
        "paper_trading": 1,
        "actionable": 0,
        "bet_placed": 0,
        "alerted": 0
    }
    default.update(kwargs)
    with sqlite3.connect(db_path) as conn:
        cols = ", ".join(default.keys())
        placeholders = ", ".join("?" for _ in default)
        conn.execute(f"INSERT INTO value_detections ({cols}) VALUES ({placeholders})", list(default.values()))

def get_last_id(db_path) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT MAX(id) FROM value_detections")
        row = cursor.fetchone()
        return row[0] if row else 0

def test_get_value_detection_by_id_missing_api_key(client, test_db):
    response = client.get("/api/value-detections/1")
    assert response.status_code == 401

def test_get_value_detection_by_id_invalid_api_key(client, test_db):
    response = client.get("/api/value-detections/1", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_get_value_detection_by_id_not_found(client, test_db, auth_headers):
    response = client.get("/api/value-detections/999", headers=auth_headers)
    assert response.status_code == 404

def test_get_value_detection_by_id_invalid_id(client, test_db, auth_headers):
    response = client.get("/api/value-detections/0", headers=auth_headers)
    assert response.status_code == 400
    
    response = client.get("/api/value-detections/-1", headers=auth_headers)
    assert response.status_code == 400

def test_get_value_detection_by_id_success(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1")
    last_id = get_last_id(test_db)
    
    response = client.get(f"/api/value-detections/{last_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["data"]["opportunity_id"] == "opt1"
    assert data["data"]["actionable"] is False

def test_get_value_detection_by_id_unsafe_db_actionable(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", actionable=1)
    last_id = get_last_id(test_db)
    response = client.get(f"/api/value-detections/{last_id}", headers=auth_headers)
    assert response.status_code == 500
    assert "Security corruption" in response.json()["detail"]
    
def test_get_value_detection_by_id_unsafe_db_bet_placed(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", bet_placed=1)
    last_id = get_last_id(test_db)
    response = client.get(f"/api/value-detections/{last_id}", headers=auth_headers)
    assert response.status_code == 500

def test_get_value_detection_by_id_unsafe_db_alerted(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", alerted=1)
    last_id = get_last_id(test_db)
    response = client.get(f"/api/value-detections/{last_id}", headers=auth_headers)
    assert response.status_code == 500
