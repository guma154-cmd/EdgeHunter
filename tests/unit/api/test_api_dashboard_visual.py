import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app
from src.edgehunter.database.schema import ensure_schema

app = create_app()
client = TestClient(app)
valid_api_key = "test_api_key"
headers = {"X-API-Key": valid_api_key}

@pytest.fixture(autouse=True)
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    ensure_schema(path)
    monkeypatch.setenv("EDGEHUNTER_DB_PATH", path)
    monkeypatch.setenv("EDGEHUNTER_API_KEY", valid_api_key)
    return path

def test_dashboard_visual_requires_api_key():
    response = client.get("/dashboard")
    assert response.status_code == 401

def test_dashboard_visual_wrong_api_key():
    response = client.get("/dashboard", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403

def test_dashboard_html_returns_200_with_html():
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    
    assert "<!DOCTYPE html>" in html
    assert "Simulated analytics dashboard" in html
    assert "Read-only" in html
    assert "<script" not in html.lower()
    assert "cdn" not in html.lower()
    assert "aposta" not in html.lower()
    assert "lucro" not in html.lower()

def test_dashboard_visual_json_endpoint():
    response = client.get("/api/dashboard/visual", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_simulated"] is True
    assert data["actionable"] is False
    assert data["not_operational_advice"] is True
    
    payload = data["data"]
    assert "title" in payload
    assert "aposta" not in str(payload).lower()

def test_endpoint_is_get_only():
    response = client.post("/dashboard", headers=headers)
    assert response.status_code == 405
    response = client.put("/dashboard", headers=headers)
    assert response.status_code == 405
