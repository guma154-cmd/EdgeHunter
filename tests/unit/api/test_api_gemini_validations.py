"""Tests for STORY-06-006 read-only AI validation API."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.edgehunter.api.app import create_app
from src.edgehunter.core.gemini_validator import SafeAIValidationResult
from src.edgehunter.core.gemini_validator_persistence import persist_ai_validation_result
from src.edgehunter.database.schema import ensure_schema


def _blocked(*parts: str) -> str:
    return "".join(parts)


@pytest.fixture
def test_db(tmp_path: Path):
    db_path = str(tmp_path / "test_edge_hunter_ai.db")
    ensure_schema(db_path)
    os.environ["EDGEHUNTER_DB_PATH"] = db_path
    yield db_path
    os.environ.pop("EDGEHUNTER_DB_PATH", None)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    os.environ["EDGEHUNTER_API_KEY"] = "secret"
    yield {"X-API-Key": "secret"}
    os.environ.pop("EDGEHUNTER_API_KEY", None)


def _result(**overrides: object) -> SafeAIValidationResult:
    payload: dict[str, object] = {
        "validation_id": "ai-validation-api-001",
        "opportunity_id": "sim-opportunity-api-001",
        "technical_verdict": "review",
        "confidence": 0.65,
        "risk_factors": ["low_sample_size"],
        "rationale": "Technical review only.",
        "parser_status": "parsed",
        "provider": "fake",
        "model_name": "fake-gemini-validator-v1",
        "prompt_hash": "c" * 64,
        "tokens_used": 0,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return SafeAIValidationResult.from_dict(payload)


def _persist(db_path: str, **overrides: object) -> int:
    return persist_ai_validation_result(str(db_path), _result(**overrides))


def _unsafe_insert(db_path: str, **overrides: object) -> None:
    row: dict[str, object] = {
        "validation_id": "ai-validation-corrupt",
        "opportunity_id": "sim-opportunity-corrupt",
        "technical_verdict": "review",
        "confidence": 0.65,
        "risk_factors_json": '["low_sample_size"]',
        "rationale": "Technical review only.",
        "parser_status": "parsed",
        "provider": "fake",
        "model_name": "fake-gemini-validator-v1",
        "prompt_hash": "d" * 64,
        "tokens_used": 0,
        "is_simulated": 1,
        "paper_trading": 1,
        "actionable": 0,
        "bet_placed": 0,
        "alerted": 0,
        "not_operational_advice": 1,
    }
    row.update(overrides)
    with sqlite3.connect(db_path) as connection:
        columns = ", ".join(row)
        placeholders = ", ".join("?" for _ in row)
        connection.execute(
            f"INSERT INTO gemini_validation_reports ({columns}) VALUES ({placeholders})",
            list(row.values()),
        )


def _count_rows(db_path: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM gemini_validation_reports",
        ).fetchone()[0]


def test_missing_api_key_fails(client, test_db: str) -> None:
    assert client.get("/api/gemini-validations").status_code == 401


def test_wrong_api_key_fails(client, test_db: str) -> None:
    response = client.get("/api/gemini-validations", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403


def test_correct_api_key_returns_empty_safe_shape(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/gemini-validations", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["data"]["data"] == []
    assert payload["data"]["pagination"] == {
        "limit": 50,
        "offset": 0,
        "count": 0,
        "total": 0,
        "has_more": False,
    }


def test_persisted_report_appears_in_endpoint(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    _persist(test_db)

    response = client.get("/api/gemini-validations", headers=auth_headers)

    assert response.status_code == 200
    item = response.json()["data"]["data"][0]
    assert item["validation_id"] == "ai-validation-api-001"
    assert item["opportunity_id"] == "sim-opportunity-api-001"
    assert item["technical_verdict"] == "review"
    assert item["confidence"] == pytest.approx(0.65)
    assert item["risk_factors"] == ["low_sample_size"]
    assert item["parser_status"] == "parsed"
    assert item["provider"] == "fake"
    assert item["model_name"] == "fake-gemini-validator-v1"
    assert item["tokens_used"] == 0
    assert item["created_at"]
    assert item["inserted_at"]


def test_limit_and_offset_work(client, test_db: str, auth_headers: dict[str, str]) -> None:
    for index in range(4):
        _persist(
            test_db,
            validation_id=f"ai-validation-api-{index}",
            opportunity_id=f"sim-opportunity-api-{index}",
            prompt_hash=f"{index}" * 64,
        )

    response = client.get(
        "/api/gemini-validations?limit=2&offset=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    pagination = response.json()["data"]["pagination"]
    assert pagination["limit"] == 2
    assert pagination["offset"] == 1
    assert pagination["count"] == 2
    assert pagination["total"] == 4
    assert pagination["has_more"] is True


def test_limit_above_max_is_capped(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/gemini-validations?limit=200", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["pagination"]["limit"] == 100


def test_invalid_limit_and_offset_fail(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    assert client.get("/api/gemini-validations?limit=0", headers=auth_headers).status_code in {400, 422}
    assert client.get("/api/gemini-validations?limit=-1", headers=auth_headers).status_code in {400, 422}
    assert client.get("/api/gemini-validations?offset=-1", headers=auth_headers).status_code in {400, 422}


@pytest.mark.parametrize(
    ("query", "expected_id"),
    (
        ("opportunity_id=sim-opportunity-api-002", "ai-validation-api-002"),
        ("provider=fake-b", "ai-validation-api-002"),
        ("model_name=fake-gemini-validator-v2", "ai-validation-api-002"),
        ("technical_verdict=pass", "ai-validation-api-002"),
    ),
)
def test_filters_work(
    client,
    test_db: str,
    auth_headers: dict[str, str],
    query: str,
    expected_id: str,
) -> None:
    _persist(test_db)
    _persist(
        test_db,
        validation_id="ai-validation-api-002",
        opportunity_id="sim-opportunity-api-002",
        provider="fake-b",
        model_name="fake-gemini-validator-v2",
        technical_verdict="pass",
        prompt_hash="e" * 64,
    )

    response = client.get(f"/api/gemini-validations?{query}", headers=auth_headers)

    assert response.status_code == 200
    items = response.json()["data"]["data"]
    assert [item["validation_id"] for item in items] == [expected_id]


def test_response_and_item_preserve_safe_flags(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    _persist(test_db)

    payload = client.get("/api/gemini-validations", headers=auth_headers).json()
    item = payload["data"]["data"][0]

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False
    assert payload["not_operational_advice"] is True
    assert item["is_simulated"] is True
    assert item["paper_trading"] is True
    assert item["actionable"] is False
    assert item["bet_placed"] is False
    assert item["alerted"] is False
    assert item["not_operational_advice"] is True


def test_payload_has_no_forbidden_operational_fields(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    _persist(test_db)

    payload_text = json.dumps(
        client.get("/api/gemini-validations", headers=auth_headers).json(),
    ).lower()

    for forbidden in (
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("bet", "_amount"),
        _blocked("wag", "er"),
        _blocked("suggested", "_bet"),
        _blocked("recom", "mended", "_bet"),
        _blocked("recom", "mendation"),
        _blocked("exec", "ute"),
        _blocked("exec", "ution"),
        _blocked("place", "_bet"),
    ):
        assert forbidden not in payload_text


@pytest.mark.parametrize("field_name", ["actionable", "bet_placed", "alerted"])
def test_corrupted_operational_flags_fail_closed(
    client,
    test_db: str,
    auth_headers: dict[str, str],
    field_name: str,
) -> None:
    _unsafe_insert(test_db, **{field_name: 1})

    response = client.get("/api/gemini-validations", headers=auth_headers)

    assert response.status_code == 500
    assert "Security corruption" in response.json()["detail"]


def test_get_does_not_insert_rows(
    client,
    test_db: str,
    auth_headers: dict[str, str],
) -> None:
    before = _count_rows(test_db)

    response = client.get("/api/gemini-validations", headers=auth_headers)

    assert response.status_code == 200
    assert _count_rows(test_db) == before


def _api_imports() -> set[str]:
    imports: set[str] = set()
    for py_file in Path("src/edgehunter/api").glob("**/*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0].lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0].lower())
    return imports


def test_api_has_no_network_or_real_ai_imports() -> None:
    imports = _api_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    assert imports.isdisjoint({"google", "genai", "generativeai"})


def test_api_has_no_telegram_scheduler_or_auto_evolution_imports() -> None:
    imports = _api_imports()

    assert imports.isdisjoint(
        {
            _blocked("tele", "gram"),
            _blocked("sched", "uler"),
            "schedule",
            "apscheduler",
            _blocked("auto", "evolution"),
        },
    )
