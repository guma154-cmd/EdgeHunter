import pytest
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app



@pytest.fixture
def client():
    return TestClient(create_app())


def test_get_reconciliation_report_unauthorized(client):
    response = client.get("/api/reconciliation/report")
    assert response.status_code == 401


def test_get_reconciliation_report_authorized(client, monkeypatch):
    monkeypatch.setenv("EDGEHUNTER_API_KEY", "test-key")
    
    # Mock the DB logic
    def mock_report(db_path):
        return {
            "summary": {
                "total_classifications": 10,
                "total_outcomes": 8,
                "matched_outcomes": 8,
                "pending_classifications": 2,
                "unmatched_outcomes": 0
            },
            "pending_classifications_sample": [],
            "is_simulated": True,
            "actionable": False,
            "not_operational_advice": True
        }
    monkeypatch.setattr("src.edgehunter.api.routes.generate_reconciliation_report", mock_report)
    
    response = client.get("/api/reconciliation/report", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "summary" in data
    assert "matched_outcomes" in data["summary"]
    assert "pending_classifications" in data["summary"]
    assert data["is_simulated"] is True
