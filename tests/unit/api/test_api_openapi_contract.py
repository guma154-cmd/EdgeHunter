import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_openapi_json_returns_200(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200

def test_openapi_metadata(client):
    response = client.get("/openapi.json")
    data = response.json()
    info = data.get("info", {})
    
    assert info.get("title") == "EdgeHunter API"
    desc = info.get("description", "").lower()
    
    # Description explicit requirements
    assert "simulated" in desc
    assert "paper trading" in desc
    assert "not" in desc and ("advice" in desc or "recommendation" in desc)
    
def test_openapi_endpoints_present(client):
    response = client.get("/openapi.json")
    data = response.json()
    paths = data.get("paths", {})
    
    assert "/api/health" in paths
    assert "/api/readiness" in paths
    assert "/api/value-detections" in paths
    assert "/api/value-detections/{id}" in paths
    assert "/api/backtests" in paths

def test_openapi_tags(client):
    response = client.get("/openapi.json")
    data = response.json()
    paths = data.get("paths", {})
    
    assert "health" in paths["/api/health"]["get"]["tags"]
    assert "readiness" in paths["/api/readiness"]["get"]["tags"]
    assert "value-detections" in paths["/api/value-detections"]["get"]["tags"]
    assert "value-detections" in paths["/api/value-detections/{id}"]["get"]["tags"]
    assert "backtests" in paths["/api/backtests"]["get"]["tags"]

def test_openapi_security_scheme(client):
    response = client.get("/openapi.json")
    data = response.json()
    components = data.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    
    assert "APIKeyHeader" in security_schemes
    scheme = security_schemes["APIKeyHeader"]
    assert scheme.get("in") == "header"
    assert scheme.get("name") == "X-API-Key"
    assert scheme.get("type") == "apiKey"

def test_openapi_prohibited_language(client):
    response = client.get("/openapi.json")
    text = response.text.lower()
    
    prohibited_terms = [
        "recommended bet",
        "suggested bet",
        "place bet",
        "execute bet",
        "stake",
        "kelly",
        "bankroll",
        "wager",
        "entrada recomendada",
        "apostar agora",
        "sinal de aposta"
    ]
    
    for term in prohibited_terms:
        assert term not in text, f"Prohibited term found in OpenAPI spec: {term}"
