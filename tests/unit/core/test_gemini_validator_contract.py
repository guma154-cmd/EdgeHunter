"""Tests for STORY-06-001 safe GeminiValidator contracts."""

from __future__ import annotations

import ast
import inspect
import math

import pytest

import src.edgehunter.core.gemini_validator as validator_module
from src.edgehunter.core.gemini_validator import (
    ParserStatus,
    SafeAIValidationInput,
    SafeAIValidationResult,
    TechnicalVerdict,
)


def _blocked(*parts: str) -> str:
    return "".join(parts)


def _valid_input_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "opportunity_id": "sim-opportunity-001",
        "match_id": "match-001",
        "league": "Brasileirao",
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.56,
        "offered_odds": 2.02,
        "expected_value": 0.1312,
        "edge_percentage": 13.12,
        "source": "consensus",
        "detection_method": "consensus_pinnacle_poisson_v1",
        "snapshot_age_seconds": 120,
        "recent_hit_rate": 0.61,
        "recent_false_positive_rate": 0.14,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
    }
    payload.update(overrides)
    return payload


def _valid_result_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "validation_id": "ai-validation-001",
        "opportunity_id": "sim-opportunity-001",
        "technical_verdict": "review",
        "confidence": 0.72,
        "risk_factors": ["odds divergence requires technical review"],
        "rationale": "Divergence technical, keep simulated review status.",
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
    return payload


def test_creates_valid_safe_ai_validation_input() -> None:
    validation_input = SafeAIValidationInput.from_dict(_valid_input_payload())

    assert validation_input.opportunity_id == "sim-opportunity-001"
    assert validation_input.true_probability == pytest.approx(0.56)
    assert validation_input.is_simulated is True
    assert validation_input.paper_trading is True
    assert validation_input.actionable is False


def test_creates_valid_safe_ai_validation_result() -> None:
    result = SafeAIValidationResult.from_dict(_valid_result_payload())

    assert result.validation_id == "ai-validation-001"
    assert result.technical_verdict is TechnicalVerdict.REVIEW
    assert result.parser_status is ParserStatus.PARSED
    assert result.provider == "fake"
    assert result.model_name == "fake-gemini-validator-v1"


def test_to_dict_is_deterministic() -> None:
    result = SafeAIValidationResult.from_dict(_valid_result_payload())

    assert result.to_dict() == result.to_dict()
    assert list(result.to_dict()) == [
        "validation_id",
        "opportunity_id",
        "technical_verdict",
        "confidence",
        "risk_factors",
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
    ]


def test_security_flags_are_preserved_in_dicts() -> None:
    validation_input = SafeAIValidationInput.from_dict(_valid_input_payload())
    result = SafeAIValidationResult.from_dict(_valid_result_payload())

    assert validation_input.to_dict()["is_simulated"] is True
    assert validation_input.to_dict()["paper_trading"] is True
    assert validation_input.to_dict()["actionable"] is False
    assert result.to_dict()["is_simulated"] is True
    assert result.to_dict()["paper_trading"] is True
    assert result.to_dict()["actionable"] is False
    assert result.to_dict()["bet_placed"] is False
    assert result.to_dict()["alerted"] is False
    assert result.to_dict()["not_operational_advice"] is True


@pytest.mark.parametrize("confidence", [-0.01, 1.01, math.nan, math.inf])
def test_confidence_outside_unit_interval_fails(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        SafeAIValidationResult.from_dict(_valid_result_payload(confidence=confidence))


@pytest.mark.parametrize("probability", [-0.01, 1.01, math.nan, math.inf])
def test_probability_outside_unit_interval_fails(probability: float) -> None:
    with pytest.raises(ValueError, match="true_probability"):
        SafeAIValidationInput.from_dict(
            _valid_input_payload(true_probability=probability),
        )


@pytest.mark.parametrize("offered_odds", [1.0, 0.0, -2.0, math.nan, math.inf])
def test_invalid_odds_fail(offered_odds: float) -> None:
    with pytest.raises(ValueError, match="offered_odds"):
        SafeAIValidationInput.from_dict(_valid_input_payload(offered_odds=offered_odds))


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("expected_value", math.nan),
        ("expected_value", math.inf),
        ("edge_percentage", math.nan),
        ("edge_percentage", -math.inf),
    ],
)
def test_nan_and_infinite_values_fail(field_name: str, bad_value: float) -> None:
    with pytest.raises(ValueError, match=field_name):
        SafeAIValidationInput.from_dict(_valid_input_payload(**{field_name: bad_value}))


@pytest.mark.parametrize(
    "field_name",
    [
        "opportunity_id",
        "match_id",
        "league",
        "market",
        "selection",
        "source",
        "detection_method",
    ],
)
def test_required_empty_string_fails(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        SafeAIValidationInput.from_dict(_valid_input_payload(**{field_name: "  "}))


def test_extra_fields_fail() -> None:
    payload = _valid_input_payload(unexpected_field="x")

    with pytest.raises(ValueError, match="unexpected"):
        SafeAIValidationInput.from_dict(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        "kelly_criterion",
        _blocked("bank", "roll"),
        "bet_amount",
        _blocked("wag", "er"),
        "suggested_bet",
        "recommended_bet",
        "recommendation",
    ],
)
def test_forbidden_field_names_fail(field_name: str) -> None:
    payload = _valid_result_payload(**{field_name: "x"})

    with pytest.raises(ValueError, match="forbidden"):
        SafeAIValidationResult.from_dict(payload)


def test_actionable_true_fails() -> None:
    with pytest.raises(ValueError, match="actionable"):
        SafeAIValidationInput.from_dict(_valid_input_payload(actionable=True))


def test_bet_placed_true_fails() -> None:
    with pytest.raises(ValueError, match="bet_placed"):
        SafeAIValidationResult.from_dict(_valid_result_payload(bet_placed=True))


def test_alerted_true_fails() -> None:
    with pytest.raises(ValueError, match="alerted"):
        SafeAIValidationResult.from_dict(_valid_result_payload(alerted=True))


@pytest.mark.parametrize(
    "rationale",
    [
        _blocked("ap", "ostar agora"),
        "criar sinal de aposta",
        "aposta recomendada para hoje",
        _blocked("place", "_bet"),
        _blocked("exec", "ute now"),
    ],
)
def test_rationale_with_operational_language_fails(rationale: str) -> None:
    with pytest.raises(ValueError, match="rationale"):
        SafeAIValidationResult.from_dict(_valid_result_payload(rationale=rationale))


def test_invalid_technical_verdict_fails() -> None:
    with pytest.raises(ValueError, match="technical_verdict"):
        SafeAIValidationResult.from_dict(
            _valid_result_payload(technical_verdict="approved"),
        )


def test_invalid_parser_status_fails() -> None:
    with pytest.raises(ValueError, match="parser_status"):
        SafeAIValidationResult.from_dict(_valid_result_payload(parser_status="ok"))


def test_negative_tokens_used_fails() -> None:
    with pytest.raises(ValueError, match="tokens_used"):
        SafeAIValidationResult.from_dict(_valid_result_payload(tokens_used=-1))


def _module_imports() -> set[str]:
    source = inspect.getsource(validator_module)
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
    return imports


def test_contract_module_has_no_network_import_or_call() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    for forbidden in ("urlopen", "request(", ".get(", ".post(", "connect("):
        assert forbidden not in source


def test_contract_module_has_no_gemini_or_google_import() -> None:
    imports = _module_imports()

    assert "google" not in imports
    assert "genai" not in imports
    assert "generativeai" not in imports


def test_contract_module_has_no_telegram() -> None:
    source = inspect.getsource(validator_module).lower()

    assert "telegram" not in source


def test_contract_module_has_no_scheduler() -> None:
    source = inspect.getsource(validator_module).lower()

    assert "scheduler" not in source


def test_contract_module_has_no_auto_evolution() -> None:
    source = inspect.getsource(validator_module).lower()

    assert "autoevolution" not in source
    assert "auto_evolution" not in source


def test_contract_module_has_no_position_sizing_terms() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("sta", "ke") not in source
    assert _blocked("kel", "ly") not in source
    assert _blocked("bank", "roll") not in source


def test_contract_module_has_no_real_bet_or_financial_execution() -> None:
    source = inspect.getsource(validator_module).lower()

    for forbidden in (
        _blocked("place", "_bet"),
        _blocked("exec", "ute"),
        _blocked("exec", "ution"),
        "real_bet",
        "financial_execution",
    ):
        assert forbidden not in source

