import os
import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_check_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "ok"
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    
def test_readiness_missing_api_key(client):
    response = client.get("/api/readiness")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API Key"

def test_readiness_invalid_api_key(client):
    response = client.get("/api/readiness", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API Key"

def test_readiness_valid_api_key(client):
    os.environ["EDGEHUNTER_API_KEY"] = "secret"
    response = client.get("/api/readiness", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "ready"
    assert data["is_simulated"] is True
