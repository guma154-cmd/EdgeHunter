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

def test_get_value_detections_missing_api_key(client, test_db):
    response = client.get("/api/value-detections")
    assert response.status_code == 401

def test_get_value_detections_invalid_api_key(client, test_db):
    response = client.get("/api/value-detections", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_get_value_detections_empty(client, test_db, auth_headers):
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["data"]["data"] == []
    assert data["data"]["pagination"]["count"] == 0

def test_get_value_detections_success(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", match_id="m1")
    insert_detection(test_db, opportunity_id="opt2", match_id="m2")
    
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    items = data["data"]["data"]
    assert len(items) == 2
    assert items[0]["opportunity_id"] == "opt2"
    assert items[0]["is_simulated"] is True
    assert items[0]["actionable"] is False
    
def test_get_value_detections_pagination(client, test_db, auth_headers):
    for i in range(5):
        insert_detection(test_db, opportunity_id=f"opt{i}", match_id=f"m{i}")
        
    response = client.get("/api/value-detections?limit=2&offset=1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    items = data["data"]["data"]
    assert len(items) == 2
    assert data["data"]["pagination"]["limit"] == 2
    assert data["data"]["pagination"]["offset"] == 1
    assert data["data"]["pagination"]["total"] == 5

def test_get_value_detections_limit_max(client, test_db, auth_headers):
    response = client.get("/api/value-detections?limit=200", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["pagination"]["limit"] == 100

def test_get_value_detections_invalid_limit(client, test_db, auth_headers):
    response = client.get("/api/value-detections?limit=0", headers=auth_headers)
    assert response.status_code == 422 

def test_get_value_detections_filters(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", source="A", match_id="m1")
    insert_detection(test_db, opportunity_id="opt2", source="B", match_id="m2")
    
    response = client.get("/api/value-detections?source=A", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]["data"]) == 1
    assert response.json()["data"]["data"][0]["opportunity_id"] == "opt1"

def test_get_value_detections_unsafe_db_actionable(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", actionable=1)
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 500
    assert "Security corruption" in response.json()["detail"]
    
def test_get_value_detections_unsafe_db_bet_placed(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", bet_placed=1)
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 500

def test_get_value_detections_unsafe_db_alerted(client, test_db, auth_headers):
    insert_detection(test_db, opportunity_id="opt1", alerted=1)
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 500
