"""Tests for STORY-06-005 simulated AI validation report persistence."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
import sqlite3

import pytest

from src.edgehunter.core import gemini_validator_persistence as persistence_module
from src.edgehunter.core.gemini_validator import (
    ParserStatus,
    SafeAIValidationResult,
    TechnicalVerdict,
)
from src.edgehunter.core.gemini_validator_persistence import (
    get_ai_validation_reports,
    list_ai_validation_reports,
    persist_ai_validation_result,
)
from src.edgehunter.database.schema import (
    EXPECTED_INDEXES,
    ensure_schema,
    get_indexes,
    get_table_columns,
)


def _blocked(*parts: str) -> str:
    return "".join(parts)


def _result(**overrides: object) -> SafeAIValidationResult:
    payload: dict[str, object] = {
        "validation_id": "ai-validation-005",
        "opportunity_id": "sim-opportunity-005",
        "technical_verdict": "review",
        "confidence": 0.72,
        "risk_factors": ["local consistency review"],
        "rationale": "Technical review remains simulated and non operational.",
        "parser_status": "parsed",
        "provider": "fake",
        "model_name": "fake-gemini-validator-v1",
        "prompt_hash": "a" * 64,
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


def _unsafe_result(**overrides: object) -> SafeAIValidationResult:
    result = _result()
    for field_name, value in overrides.items():
        object.__setattr__(result, field_name, value)
    return result


def _rows(db_path: Path) -> list[sqlite3.Row]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            "SELECT * FROM gemini_validation_reports ORDER BY id",
        ).fetchall()
    finally:
        connection.close()


def test_schema_creates_gemini_validation_reports_table(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    assert ensure_schema(str(db_path)) is True

    assert get_table_columns(str(db_path), "gemini_validation_reports") == (
        "id",
        "validation_id",
        "opportunity_id",
        "technical_verdict",
        "confidence",
        "risk_factors_json",
        "rationale",
        "parser_status",
        "provider",
        "model_name",
        "prompt_hash",
        "tokens_used",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
        "created_at",
        "inserted_at",
    )


def test_schema_creates_ai_report_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    assert ensure_schema(str(db_path)) is True

    assert {
        "idx_gemini_validation_reports_opportunity",
        "idx_gemini_validation_reports_model_prompt",
        "idx_gemini_validation_reports_created",
    }.issubset(get_indexes(str(db_path)))
    assert set(EXPECTED_INDEXES).issubset(get_indexes(str(db_path)))


def test_persists_valid_report(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    result = _result()

    row_id = persist_ai_validation_result(str(db_path), result)

    assert row_id > 0
    row = _rows(db_path)[0]
    assert row["id"] == row_id
    assert row["validation_id"] == result.validation_id
    assert row["opportunity_id"] == result.opportunity_id
    assert row["technical_verdict"] == TechnicalVerdict.REVIEW.value
    assert row["confidence"] == pytest.approx(0.72)
    assert row["rationale"] == result.rationale
    assert row["parser_status"] == ParserStatus.PARSED.value
    assert row["provider"] == "fake"
    assert row["model_name"] == "fake-gemini-validator-v1"
    assert row["prompt_hash"] == "a" * 64
    assert row["tokens_used"] == 0
    assert row["created_at"]
    assert row["inserted_at"]


def test_persistence_is_idempotent_by_validation_id(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    result = _result()

    first_id = persist_ai_validation_result(str(db_path), result)
    second_id = persist_ai_validation_result(str(db_path), result)

    assert first_id == second_id
    assert len(_rows(db_path)) == 1


def test_query_returns_persisted_report(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    result = _result()
    row_id = persist_ai_validation_result(str(db_path), result)

    reports = get_ai_validation_reports(str(db_path))

    assert len(reports) == 1
    assert reports[0]["id"] == row_id
    assert reports[0]["validation_id"] == result.validation_id
    assert reports[0]["risk_factors"] == ["local consistency review"]
    assert reports[0]["created_at"]
    assert reports[0]["inserted_at"]


def test_query_can_filter_by_opportunity_id(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    first = _result()
    second = _result(
        validation_id="ai-validation-006",
        opportunity_id="sim-opportunity-006",
        prompt_hash="b" * 64,
    )

    persist_ai_validation_result(str(db_path), first)
    persist_ai_validation_result(str(db_path), second)

    reports = get_ai_validation_reports(str(db_path), opportunity_id="sim-opportunity-006")

    assert [report["validation_id"] for report in reports] == ["ai-validation-006"]


def test_list_reports_supports_filters(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    first = _result()
    second = _result(
        validation_id="ai-validation-006",
        opportunity_id="sim-opportunity-006",
        provider="fake-b",
        model_name="fake-gemini-validator-v2",
        technical_verdict="pass",
        prompt_hash="b" * 64,
    )

    persist_ai_validation_result(str(db_path), first)
    persist_ai_validation_result(str(db_path), second)

    result = list_ai_validation_reports(
        str(db_path),
        opportunity_id="sim-opportunity-006",
        provider="fake-b",
        model_name="fake-gemini-validator-v2",
        technical_verdict="pass",
    )

    assert [item["validation_id"] for item in result["data"]] == ["ai-validation-006"]
    assert result["filters"] == {
        "opportunity_id": "sim-opportunity-006",
        "provider": "fake-b",
        "model_name": "fake-gemini-validator-v2",
        "technical_verdict": "pass",
    }


def test_list_reports_supports_pagination(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    for index in range(5):
        persist_ai_validation_result(
            str(db_path),
            _result(
                validation_id=f"ai-validation-{index:03d}",
                opportunity_id=f"sim-opportunity-{index:03d}",
                prompt_hash=f"{index}" * 64,
            ),
        )

    result = list_ai_validation_reports(str(db_path), limit=2, offset=1)

    assert len(result["data"]) == 2
    assert result["pagination"] == {
        "limit": 2,
        "offset": 1,
        "count": 2,
        "total": 5,
        "has_more": True,
    }


def test_list_reports_caps_limit_at_100(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    ensure_schema(str(db_path))

    result = list_ai_validation_reports(str(db_path), limit=200)

    assert result["pagination"]["limit"] == 100


@pytest.mark.parametrize(
    ("limit", "offset", "message"),
    (
        (0, 0, "limit"),
        (-1, 0, "limit"),
        (50, -1, "offset"),
    ),
)
def test_list_reports_rejects_invalid_pagination(
    tmp_path: Path,
    limit: int,
    offset: int,
    message: str,
) -> None:
    db_path = tmp_path / "edgehunter.db"
    ensure_schema(str(db_path))

    with pytest.raises(ValueError, match=message):
        list_ai_validation_reports(str(db_path), limit=limit, offset=offset)


def test_risk_factors_are_serialized_as_json(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    result = _result(risk_factors=["model drift", "odds divergence"])

    persist_ai_validation_result(str(db_path), result)

    row = _rows(db_path)[0]
    assert json.loads(row["risk_factors_json"]) == ["model drift", "odds divergence"]
    assert row["risk_factors_json"] == '["model drift","odds divergence"]'


def test_security_flags_are_preserved(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    persist_ai_validation_result(str(db_path), _result())

    row = _rows(db_path)[0]
    assert row["is_simulated"] == 1
    assert row["paper_trading"] == 1
    assert row["actionable"] == 0
    assert row["bet_placed"] == 0
    assert row["alerted"] == 0
    assert row["not_operational_advice"] == 1


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    (
        ("is_simulated", False, "simulated"),
        ("paper_trading", False, "paper_trading"),
        ("actionable", True, "actionable"),
        ("bet_placed", True, "placed"),
        ("alerted", True, "alerted"),
        ("not_operational_advice", False, "not_operational_advice"),
    ),
)
def test_rejects_unsafe_flags(
    tmp_path: Path,
    field_name: str,
    unsafe_value: bool,
    message: str,
) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match=message):
        persist_ai_validation_result(
            str(db_path),
            _unsafe_result(**{field_name: unsafe_value}),
        )


def test_operational_rationale_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="rationale"):
        persist_ai_validation_result(
            str(db_path),
            _unsafe_result(rationale=_blocked("ap", "ostar agora")),
        )


def test_operational_risk_factor_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="risk_factors"):
        persist_ai_validation_result(
            str(db_path),
            _unsafe_result(risk_factors=(_blocked("bank", "roll exposure"),)),
        )


def test_confidence_outside_range_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="confidence"):
        persist_ai_validation_result(str(db_path), _unsafe_result(confidence=1.01))


def test_negative_tokens_used_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="tokens_used"):
        persist_ai_validation_result(str(db_path), _unsafe_result(tokens_used=-1))


def test_rejects_non_result_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="SafeAIValidationResult"):
        persist_ai_validation_result(str(db_path), object())  # type: ignore[arg-type]


def test_schema_does_not_store_position_sizing_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    assert ensure_schema(str(db_path)) is True
    columns = {column.lower() for column in get_table_columns(str(db_path), "gemini_validation_reports")}

    assert _blocked("sta", "ke") not in columns
    assert _blocked("kel", "ly") not in columns
    assert _blocked("bank", "roll") not in columns
    assert _blocked("bet", "_amount") not in columns
    assert _blocked("wag", "er") not in columns


def test_schema_does_not_store_operational_suggestion_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    assert ensure_schema(str(db_path)) is True
    columns = {column.lower() for column in get_table_columns(str(db_path), "gemini_validation_reports")}

    assert _blocked("recom", "mendation") not in columns
    assert _blocked("suggested", "_bet") not in columns
    assert _blocked("place", "_bet") not in columns


def _module_imports() -> set[str]:
    source = inspect.getsource(persistence_module)
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
    return imports


def test_persistence_module_has_no_network_import_or_call() -> None:
    source = inspect.getsource(persistence_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    for forbidden in ("urlopen", "request(", ".post("):
        assert forbidden not in source


def test_persistence_module_has_no_real_gemini_or_google_import() -> None:
    imports = _module_imports()

    assert "google" not in imports
    assert "genai" not in imports
    assert "generativeai" not in imports


def test_persistence_module_has_no_telegram_or_scheduler() -> None:
    source = inspect.getsource(persistence_module).lower()

    assert _blocked("tele", "gram") not in source
    assert _blocked("sched", "uler") not in source


def test_persistence_module_has_no_auto_evolution() -> None:
    source = inspect.getsource(persistence_module).lower()

    assert _blocked("auto", "evolution") not in source
    assert _blocked("auto", "_evolution") not in source


def test_persistence_module_has_no_api() -> None:
    source = inspect.getsource(persistence_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"fastapi"})
    assert "apirouter" not in source


def test_persistence_module_has_no_real_bet_or_financial_execution() -> None:
    source = inspect.getsource(persistence_module).lower()

    for forbidden in (
        _blocked("place", "_bet"),
        "real_bet",
        "financial_execution",
    ):
        assert forbidden not in source
