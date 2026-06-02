import sqlite3
import pytest
from fastapi.testclient import TestClient

from src.edgehunter.api.app import create_app
from src.edgehunter.database.schema import ensure_schema

client = TestClient(create_app())
valid_api_key = "test_api_key"

@pytest.fixture(autouse=True)
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    ensure_schema(path)
    monkeypatch.setenv("EDGEHUNTER_DB_PATH", path)
    monkeypatch.setenv("EDGEHUNTER_API_KEY", valid_api_key)
    return path

def test_dashboard_visual_xss_injection(monkeypatch):
    # Mocking generate_dashboard_summary to return XSS string in the summary
    from src.edgehunter.api import routes
    
    def fake_summary(*args, **kwargs):
        xss_string = "<script>alert('hack')</script>"
        return {
            "total_matches": xss_string,
            "simulated_outcomes": {xss_string: 1},
            "threshold_suggestion": xss_string
        }

    monkeypatch.setattr(routes, "generate_dashboard_summary", fake_summary)
    
    response = client.get("/dashboard", headers={"X-API-Key": valid_api_key})
    if response.status_code != 200:
        print("FAIL:", response.text)
    assert response.status_code == 200
    html = response.text
    
    # Assert that <script is escaped and doesn't appear exactly as active HTML tag
    assert "<script>" not in html.lower()
    assert "&lt;script&gt;" in html.lower()
    assert "alert(&#x27;hack&#x27;)" in html

def test_dashboard_visual_db_failure(monkeypatch):
    from src.edgehunter.api import routes
    
    def fake_read(*args, **kwargs):
        raise sqlite3.Error("Disk full")

    monkeypatch.setattr(routes, "_read_dashboard_inputs", fake_read)
    
    response = client.get("/dashboard", headers={"X-API-Key": valid_api_key})
    assert response.status_code == 500
    assert "Disk full" in response.text
    
    response_json = client.get("/api/dashboard/visual", headers={"X-API-Key": valid_api_key})
    assert response_json.status_code == 500

def test_dashboard_visual_value_error(monkeypatch):
    from src.edgehunter.api import routes
    
    def fake_read(*args, **kwargs):
        raise ValueError("Invalid metric simulation")

    monkeypatch.setattr(routes, "_read_dashboard_inputs", fake_read)
    
    response = client.get("/dashboard", headers={"X-API-Key": valid_api_key})
    assert response.status_code == 400
    assert "Invalid metric simulation" in response.text
