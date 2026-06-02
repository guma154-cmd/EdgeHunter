import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sqlite3
import os

from src.edgehunter.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test_api_key"}

@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, {"EDGEHUNTER_API_KEY": "test_api_key"}):
        yield

@patch("src.edgehunter.api.routes.get_db_path")
def test_get_migrations_status(mock_get_db_path, client, auth_headers, tmp_path):
    db_path = str(tmp_path / "test.db")
    mock_get_db_path.return_value = db_path
    
    response = client.get("/api/migrations/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["not_operational_advice"] is True
    assert "registry_valid" in data["data"]
    assert "up_to_date" in data["data"]
    assert "pending_count" in data["data"]

@patch("src.edgehunter.api.routes.get_db_path")
def test_get_migrations_plan(mock_get_db_path, client, auth_headers, tmp_path):
    db_path = str(tmp_path / "test.db")
    mock_get_db_path.return_value = db_path
    
    response = client.get("/api/migrations/plan", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["not_operational_advice"] is True
    assert data["data"]["execution_mode"] == "DRY_RUN"
    assert "items" in data["data"]

@patch("src.edgehunter.api.routes.get_db_path")
def test_get_migrations_journal(mock_get_db_path, client, auth_headers, tmp_path):
    db_path = str(tmp_path / "test.db")
    mock_get_db_path.return_value = db_path
    
    # Empty DB, should return empty data without failing
    response = client.get("/api/migrations/journal", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["not_operational_advice"] is True
    assert data["data"]["data"] == []
