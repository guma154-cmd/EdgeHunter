"""Tests for STORY-06-004 offline fake GeminiValidator flow."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from typing import Any

import pytest

import src.edgehunter.core.gemini_validator as validator_module
from src.edgehunter.core.gemini_validator import (
    FAKE_GEMINI_VALIDATION_MODEL,
    FAKE_GEMINI_VALIDATION_PROVIDER,
    FakeGeminiValidationClient,
    ParserStatus,
    SafeAIValidationInput,
    SafeAIValidationResult,
    TechnicalVerdict,
    build_gemini_validation_prompt,
    validate_opportunity_offline,
)


def _blocked(*parts: str) -> str:
    return "".join(parts)


def _validation_input(**overrides: Any) -> SafeAIValidationInput:
    payload: dict[str, Any] = {
        "opportunity_id": "sim-opportunity-004",
        "match_id": "match-004",
        "league": "Brazil Serie A",
        "market": "home_win",
        "selection": "Home Team",
        "true_probability": 0.58,
        "offered_odds": 2.05,
        "expected_value": 0.189,
        "edge_percentage": 18.9,
        "source": "value_detector",
        "detection_method": "threshold_v1",
        "snapshot_age_seconds": 42,
        "recent_hit_rate": 0.53,
        "recent_false_positive_rate": 0.21,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
    }
    payload.update(overrides)
    return SafeAIValidationInput(**payload)


def _assert_safe_fallback(result: SafeAIValidationResult) -> None:
    assert result.technical_verdict is TechnicalVerdict.INVALID_RESPONSE
    assert result.confidence == pytest.approx(0.0)
    assert result.risk_factors == ("invalid_or_unsafe_ai_response",)
    assert result.rationale == "AI validation response could not be safely parsed."
    assert result.parser_status is ParserStatus.FAILED
    assert result.is_simulated is True
    assert result.paper_trading is True
    assert result.actionable is False
    assert result.bet_placed is False
    assert result.alerted is False
    assert result.not_operational_advice is True


def test_fake_client_returns_valid_json_contract() -> None:
    raw_response = FakeGeminiValidationClient().validate("safe offline prompt")
    payload = json.loads(raw_response)

    assert set(payload) == {
        "technical_verdict",
        "confidence",
        "risk_factors",
        "rationale",
    }
    assert payload["technical_verdict"] in {"pass", "review", "reject"}
    assert 0.0 <= payload["confidence"] <= 1.0
    assert isinstance(payload["risk_factors"], list)
    assert payload["risk_factors"]
    assert isinstance(payload["rationale"], str)


def test_fake_client_is_deterministic_for_same_prompt() -> None:
    client = FakeGeminiValidationClient()

    assert client.validate("same prompt") == client.validate("same prompt")


def test_fake_client_rejects_blank_prompt() -> None:
    with pytest.raises(ValueError):
        FakeGeminiValidationClient().validate("  ")


def test_fake_client_output_has_no_operational_language() -> None:
    raw_response = FakeGeminiValidationClient().validate("safe offline prompt").lower()

    for forbidden in (
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("ap", "ostar"),
        _blocked("place", "_bet"),
    ):
        assert forbidden not in raw_response


def test_offline_flow_returns_safe_validation_result() -> None:
    validation_input = _validation_input()

    result = validate_opportunity_offline(validation_input)

    assert isinstance(result, SafeAIValidationResult)
    assert result.opportunity_id == "sim-opportunity-004"
    assert result.technical_verdict in {
        TechnicalVerdict.PASS,
        TechnicalVerdict.REVIEW,
        TechnicalVerdict.REJECT,
    }
    assert result.parser_status is ParserStatus.PARSED


def test_offline_flow_sets_fake_provider_model_tokens_and_flags() -> None:
    result = validate_opportunity_offline(_validation_input())
    payload = result.to_dict()

    assert payload["provider"] == FAKE_GEMINI_VALIDATION_PROVIDER
    assert payload["model_name"] == FAKE_GEMINI_VALIDATION_MODEL
    assert payload["tokens_used"] == 0
    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False
    assert payload["not_operational_advice"] is True


def test_offline_flow_computes_deterministic_prompt_hash() -> None:
    validation_input = _validation_input()
    prompt = build_gemini_validation_prompt(validation_input)
    expected_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    first = validate_opportunity_offline(validation_input)
    second = validate_opportunity_offline(validation_input)

    assert first.prompt_hash == expected_hash
    assert second.prompt_hash == expected_hash
    assert first.prompt_hash == second.prompt_hash


def test_offline_flow_is_deterministic_for_same_input() -> None:
    validation_input = _validation_input()

    first = validate_opportunity_offline(validation_input)
    second = validate_opportunity_offline(validation_input)

    assert first.to_dict() == second.to_dict()


def test_offline_flow_sends_built_prompt_to_client() -> None:
    class RecordingClient:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def validate(self, prompt: str) -> str:
            self.prompts.append(prompt)
            return FakeGeminiValidationClient().validate(prompt)

    validation_input = _validation_input()
    client = RecordingClient()

    validate_opportunity_offline(validation_input, client=client)

    assert client.prompts == [build_gemini_validation_prompt(validation_input)]


def test_offline_flow_does_not_mutate_input_payload() -> None:
    validation_input = _validation_input()
    before = validation_input.to_dict()

    validate_opportunity_offline(validation_input)

    assert validation_input.to_dict() == before


def test_invalid_client_response_returns_safe_fallback() -> None:
    class InvalidClient:
        def validate(self, prompt: str) -> str:
            return "not json"

    result = validate_opportunity_offline(_validation_input(), client=InvalidClient())

    _assert_safe_fallback(result)


def test_unsafe_client_response_returns_safe_fallback() -> None:
    class UnsafeClient:
        def validate(self, prompt: str) -> str:
            return json.dumps(
                {
                    "technical_verdict": "review",
                    "confidence": 0.74,
                    "risk_factors": [_blocked("bank", "roll exposure")],
                    "rationale": "Unsafe payload.",
                },
            )

    result = validate_opportunity_offline(_validation_input(), client=UnsafeClient())

    _assert_safe_fallback(result)


def test_client_error_returns_safe_fallback() -> None:
    class ErrorClient:
        def validate(self, prompt: str) -> str:
            raise RuntimeError("local client failed")

    result = validate_opportunity_offline(_validation_input(), client=ErrorClient())

    _assert_safe_fallback(result)


def test_invalid_client_object_returns_safe_fallback() -> None:
    result = validate_opportunity_offline(_validation_input(), client=object())

    _assert_safe_fallback(result)


def test_invalid_input_object_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_opportunity_offline({"opportunity_id": "sim-opportunity-004"})


def test_invalid_response_fallback_preserves_context() -> None:
    class InvalidClient:
        def validate(self, prompt: str) -> str:
            return "not json"

    validation_input = _validation_input()
    result = validate_opportunity_offline(validation_input, client=InvalidClient())
    prompt = build_gemini_validation_prompt(validation_input)

    assert result.opportunity_id == validation_input.opportunity_id
    assert result.provider == FAKE_GEMINI_VALIDATION_PROVIDER
    assert result.model_name == FAKE_GEMINI_VALIDATION_MODEL
    assert result.prompt_hash == hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def test_fallback_output_has_no_operational_language() -> None:
    class ErrorClient:
        def validate(self, prompt: str) -> str:
            raise RuntimeError("local client failed")

    result = validate_opportunity_offline(_validation_input(), client=ErrorClient())
    fallback_text = json.dumps(result.to_dict()).lower()

    for forbidden in (
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("ap", "ostar"),
        _blocked("place", "_bet"),
    ):
        assert forbidden not in fallback_text


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


def test_offline_module_has_no_network_import_or_call() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    for forbidden in ("urlopen", "request(", ".get(", ".post(", "connect("):
        assert forbidden not in source


def test_offline_module_has_no_gemini_or_google_sdk_import() -> None:
    imports = _module_imports()

    assert "google" not in imports
    assert "genai" not in imports
    assert "generativeai" not in imports


def test_offline_module_has_no_api_or_persistence() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"fastapi", "sqlite3"})
    assert "apirouter" not in source
    assert "insert into" not in source
    assert "create table" not in source


def test_offline_module_has_no_telegram_or_scheduler() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("tele", "gram") not in source
    assert _blocked("sched", "uler") not in source


def test_offline_module_has_no_auto_evolution() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("auto", "evolution") not in source
    assert _blocked("auto", "_evolution") not in source


def test_offline_module_has_no_position_sizing_terms() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("sta", "ke") not in source
    assert _blocked("kel", "ly") not in source
    assert _blocked("bank", "roll") not in source


def test_offline_module_has_no_real_bet_or_financial_execution() -> None:
    source = inspect.getsource(validator_module).lower()

    for forbidden in (
        _blocked("place", "_bet"),
        _blocked("exec", "ute"),
        _blocked("exec", "ution"),
        "real_bet",
        "financial_execution",
    ):
        assert forbidden not in source
