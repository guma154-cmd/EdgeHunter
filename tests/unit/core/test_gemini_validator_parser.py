"""Tests for STORY-06-003 safe GeminiValidator response parser."""

from __future__ import annotations

import ast
import inspect
import json

import pytest

import src.edgehunter.core.gemini_validator as validator_module
from src.edgehunter.core.gemini_validator import (
    ParserStatus,
    TechnicalVerdict,
    parse_gemini_validation_response,
)


def _blocked(*parts: str) -> str:
    return "".join(parts)


def _raw_payload(**overrides: object) -> str:
    payload: dict[str, object] = {
        "technical_verdict": "review",
        "confidence": 0.74,
        "risk_factors": ["odds divergence requires technical review"],
        "rationale": "Evidence is mixed; keep technical review.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def _parse(raw_response: str):
    return parse_gemini_validation_response(
        raw_response,
        opportunity_id="sim-opportunity-001",
        provider="fake",
        model_name="fake-gemini-validator-v1",
        prompt_hash="a" * 64,
    )


def _assert_safe_fallback(result) -> None:
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


def test_parse_valid_plain_json() -> None:
    result = _parse(_raw_payload())

    assert result.technical_verdict is TechnicalVerdict.REVIEW
    assert result.confidence == pytest.approx(0.74)
    assert result.parser_status is ParserStatus.PARSED
    assert result.risk_factors == ("odds divergence requires technical review",)


def test_parse_json_inside_markdown_fence() -> None:
    result = _parse(f"```json\n{_raw_payload(technical_verdict='pass')}\n```")

    assert result.technical_verdict is TechnicalVerdict.PASS
    assert result.parser_status is ParserStatus.RECOVERED


def test_parse_recoverable_json_with_surrounding_text() -> None:
    result = _parse(f"analysis:\n{_raw_payload(technical_verdict='reject')}\nend")

    assert result.technical_verdict is TechnicalVerdict.REJECT
    assert result.parser_status is ParserStatus.RECOVERED


def test_malformed_json_returns_safe_fallback() -> None:
    _assert_safe_fallback(_parse('{"technical_verdict": "review",'))


def test_empty_response_returns_safe_fallback() -> None:
    _assert_safe_fallback(_parse("  "))


def test_invalid_technical_verdict_returns_failed_fallback() -> None:
    result = _parse(_raw_payload(technical_verdict="approved"))

    _assert_safe_fallback(result)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_unit_interval_returns_failed_fallback(
    confidence: float,
) -> None:
    _assert_safe_fallback(_parse(_raw_payload(confidence=confidence)))


def test_extra_field_returns_failed_fallback() -> None:
    _assert_safe_fallback(_parse(_raw_payload(extra="x")))


@pytest.mark.parametrize(
    "field_name",
    [
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("recom", "mendation"),
        _blocked("exec", "ute"),
    ],
)
def test_forbidden_field_returns_failed_fallback(field_name: str) -> None:
    _assert_safe_fallback(_parse(_raw_payload(**{field_name: "x"})))


@pytest.mark.parametrize(
    "rationale",
    [
        _blocked("ap", "ostar agora"),
        _blocked("sinal", " de ", "ap", "osta"),
        _blocked("place", "_bet"),
    ],
)
def test_operational_rationale_returns_failed_fallback(rationale: str) -> None:
    _assert_safe_fallback(_parse(_raw_payload(rationale=rationale)))


def test_operational_risk_factor_returns_failed_fallback() -> None:
    result = _parse(
        _raw_payload(risk_factors=[_blocked("bank", "roll exposure")]),
    )

    _assert_safe_fallback(result)


def test_fallback_does_not_repeat_forbidden_language() -> None:
    result = _parse(
        _raw_payload(
            rationale=_blocked("ap", "ostar agora"),
            **{_blocked("sta", "ke"): "x"},
        ),
    )
    fallback_text = json.dumps(result.to_dict()).lower()

    for forbidden in (
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("ap", "ostar"),
        _blocked("place", "_bet"),
    ):
        assert forbidden not in fallback_text


def test_parser_status_parsed_for_plain_json() -> None:
    assert _parse(_raw_payload()).parser_status is ParserStatus.PARSED


def test_parser_status_recovered_for_markdown_or_text_json() -> None:
    assert _parse(f"```json\n{_raw_payload()}\n```").parser_status is (
        ParserStatus.RECOVERED
    )
    assert _parse(f"prefix {_raw_payload()} suffix").parser_status is (
        ParserStatus.RECOVERED
    )


def test_parser_status_failed_for_unsafe_response() -> None:
    result = _parse(_raw_payload(**{_blocked("recom", "mendation"): "x"}))

    assert result.parser_status is ParserStatus.FAILED


def test_security_flags_are_preserved() -> None:
    result = _parse(_raw_payload())
    payload = result.to_dict()

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False
    assert payload["not_operational_advice"] is True


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


def test_parser_module_has_no_network_import_or_call() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    for forbidden in ("urlopen", "request(", ".get(", ".post(", "connect("):
        assert forbidden not in source


def test_parser_module_has_no_gemini_or_google_import() -> None:
    imports = _module_imports()

    assert "google" not in imports
    assert "genai" not in imports
    assert "generativeai" not in imports


def test_parser_module_has_no_api_or_persistence() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"fastapi", "sqlite3"})
    assert "apirouter" not in source
    assert "insert into" not in source
    assert "create table" not in source


def test_parser_module_has_no_telegram_or_scheduler() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("tele", "gram") not in source
    assert _blocked("sched", "uler") not in source


def test_parser_module_has_no_auto_evolution() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("auto", "evolution") not in source
    assert _blocked("auto", "_evolution") not in source


def test_parser_module_has_no_position_sizing_terms() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("sta", "ke") not in source
    assert _blocked("kel", "ly") not in source
    assert _blocked("bank", "roll") not in source


def test_parser_module_has_no_real_bet_or_financial_execution() -> None:
    source = inspect.getsource(validator_module).lower()

    for forbidden in (
        _blocked("place", "_bet"),
        _blocked("exec", "ute"),
        _blocked("exec", "ution"),
        "real_bet",
        "financial_execution",
    ):
        assert forbidden not in source

