import os
import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app

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

def test_get_backtests_missing_api_key(client):
    response = client.get("/api/backtests")
    assert response.status_code == 401

def test_get_backtests_invalid_api_key(client):
    response = client.get("/api/backtests", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_get_backtests_empty_success(client, auth_headers):
    response = client.get("/api/backtests", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_simulated"] is True
    assert data["paper_trading"] is True
    assert data["actionable"] is False
    assert data["not_operational_advice"] is True
    
    assert "data" in data
    assert data["data"]["data"] == []
    assert data["data"]["pagination"]["limit"] == 50
    assert data["data"]["pagination"]["offset"] == 0
    assert data["data"]["pagination"]["count"] == 0
    assert data["data"]["pagination"]["has_more"] is False

def test_get_backtests_custom_limit_offset(client, auth_headers):
    response = client.get("/api/backtests?limit=10&offset=20", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["pagination"]["limit"] == 10
    assert data["data"]["pagination"]["offset"] == 20

def test_get_backtests_invalid_limit(client, auth_headers):
    response = client.get("/api/backtests?limit=0", headers=auth_headers)
    assert response.status_code == 422  # FastAPI Query validation or 400
    
    response = client.get("/api/backtests?limit=-1", headers=auth_headers)
    assert response.status_code == 422

def test_get_backtests_invalid_offset(client, auth_headers):
    response = client.get("/api/backtests?offset=-1", headers=auth_headers)
    assert response.status_code == 422

def test_get_backtests_max_limit(client, auth_headers):
    # Depending on FastAPI validation, it could pass query then limit inside helper
    response = client.get("/api/backtests?limit=200", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["pagination"]["limit"] == 100  # Truncated to 100
