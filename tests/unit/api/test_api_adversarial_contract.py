import os
import sqlite3
import pytest
import ast
from pathlib import Path
from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app
from src.edgehunter.api.contracts import build_safe_api_response
from src.edgehunter.database.schema import ensure_schema

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_edge_hunter_adv.db")
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

# 1. Autenticação
def test_auth_adversarial(client, test_db):
    os.environ["EDGEHUNTER_API_KEY"] = "secret"
    # Sem header
    assert client.get("/api/value-detections").status_code == 401
    assert client.get("/api/backtests").status_code == 401
    
    # Header vazio
    assert client.get("/api/value-detections", headers={"X-API-Key": ""}).status_code == 401
    
    # Header errado
    assert client.get("/api/value-detections", headers={"X-API-Key": "wrong"}).status_code == 403
    
    # Valor com espaços (se esperado rejeitar ou lidar, depende do .env. Se .env=secret, " secret " falha)
    assert client.get("/api/value-detections", headers={"X-API-Key": " secret "}).status_code == 403
    
    # Header duplicado (TestClient geralmente não permite múltiplos headers com chave idêntica sem mesclar, mas podemos testar envio de X-API-KEY case insensitive)
    assert client.get("/api/value-detections", headers={"x-api-key": "secret"}).status_code == 200

    # /api/health permanece público
    assert client.get("/api/health").status_code == 200

# 2. Payload proibido
@pytest.mark.parametrize("forbidden_field, value", [
    ("stake", 10), ("kelly", 0.5), ("kelly_criterion", 0.1), ("bankroll", 100),
    ("bet_amount", 5), ("wager", 1), ("suggested_bet", 10), ("recommended_bet", 10),
    ("execute", True), ("execution", True), ("place_bet", True), ("entrada", 50),
    ("actionable", True), ("bet_placed", True), ("alerted", True)
])
def test_build_safe_api_response_forbidden_fields(forbidden_field, value):
    payload = {"opportunity_id": "opt1", forbidden_field: value}
    with pytest.raises(ValueError):
        build_safe_api_response(payload)

# 3. Banco corrompido
def test_db_corruption_flags(client, test_db, auth_headers):
    # Insert corrupted row with actionable=1
    with sqlite3.connect(test_db) as conn:
        conn.execute("INSERT INTO value_detections (opportunity_id, match_id, market, selection, true_probability, offered_odds, expected_value, edge_percentage, source, detection_method, created_at, actionable) VALUES ('opt1', 'm1', '1x2', 'home', 0.5, 2.1, 0.05, 5.0, 's', 'dm', '2026', 1)")
    
    response = client.get("/api/value-detections", headers=auth_headers)
    assert response.status_code == 500
    assert "Security corruption detected" in response.text
    
    # Test Detail
    response = client.get("/api/value-detections/1", headers=auth_headers)
    assert response.status_code == 500
    assert "Security corruption detected" in response.text

# 4. Paginação adversarial
def test_pagination_adversarial(client, test_db, auth_headers):
    assert client.get("/api/value-detections?limit=0", headers=auth_headers).status_code in [400, 422]
    assert client.get("/api/value-detections?limit=-1", headers=auth_headers).status_code in [400, 422]
    assert client.get("/api/value-detections?offset=-1", headers=auth_headers).status_code in [400, 422]
    assert client.get("/api/value-detections?limit=not_an_int", headers=auth_headers).status_code == 422
    assert client.get("/api/value-detections?offset=invalid", headers=auth_headers).status_code == 422
    
    # Limit max cap
    response = client.get("/api/value-detections?limit=200", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["pagination"]["limit"] == 100

# 5. OpenAPI adversarial
def test_openapi_adversarial(client):
    response = client.get("/openapi.json")
    text = response.text.lower()
    prohibited_terms = [
        "place bet", "recommended bet", "suggested bet", "stake",
        "kelly", "bankroll", "wager", "apostar agora",
        "entrada recomendada", "sinal de aposta"
    ]
    for term in prohibited_terms:
        assert term not in text

# 6. Read-only (não altera banco)
def test_read_only_nature(client, test_db, auth_headers):
    def count_rows():
        with sqlite3.connect(test_db) as conn:
            return conn.execute("SELECT COUNT(*) FROM value_detections").fetchone()[0]
    
    initial = count_rows()
    client.get("/api/value-detections", headers=auth_headers)
    client.get("/api/value-detections/1", headers=auth_headers)
    client.get("/api/backtests", headers=auth_headers)
    
    assert count_rows() == initial

# 7. Guardrails de integração (Static Analysis AST)
def test_static_analysis_for_prohibited_imports():
    api_dir = Path("src/edgehunter/api")
    prohibited_modules = [
        "requests", "httpx", "urllib", 
        "telegram", "discord",
        "apscheduler", "schedule", "celery",
        "gemini", "google.generativeai",
        "autoevolution", "playwright", "selenium"
    ]
    
    for py_file in api_dir.glob("**/*.py"):
        code = py_file.read_text(encoding="utf-8")
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for mod in prohibited_modules:
                        assert not alias.name.startswith(mod), f"Prohibited import {alias.name} found in {py_file.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for mod in prohibited_modules:
                        assert not node.module.startswith(mod), f"Prohibited import {node.module} found in {py_file.name}"
