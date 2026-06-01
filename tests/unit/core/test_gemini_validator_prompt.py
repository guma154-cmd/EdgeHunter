"""Tests for STORY-06-002 safe GeminiValidator prompt builder."""

from __future__ import annotations

import ast
import inspect

import pytest

import src.edgehunter.core.gemini_validator as validator_module
from src.edgehunter.core.gemini_validator import (
    SafeAIValidationInput,
    build_gemini_validation_prompt,
)


def _blocked(*parts: str) -> str:
    return "".join(parts)


def _validation_input() -> SafeAIValidationInput:
    return SafeAIValidationInput.from_dict(
        {
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
        },
    )


def _prompt() -> str:
    return build_gemini_validation_prompt(_validation_input())


def test_creates_valid_prompt_from_safe_input() -> None:
    prompt = _prompt()

    assert isinstance(prompt, str)
    assert prompt.strip() == prompt
    assert "sim-opportunity-001" in prompt


def test_prompt_is_deterministic() -> None:
    validation_input = _validation_input()

    assert build_gemini_validation_prompt(validation_input) == (
        build_gemini_validation_prompt(validation_input)
    )


def test_prompt_contains_essential_allowed_fields() -> None:
    prompt = _prompt()

    for field_name in (
        "opportunity_id",
        "match_id",
        "league",
        "market",
        "selection",
        "true_probability",
        "offered_odds",
        "expected_value",
        "edge_percentage",
        "source",
        "detection_method",
        "snapshot_age_seconds",
        "recent_hit_rate",
        "recent_false_positive_rate",
        "is_simulated",
        "paper_trading",
        "actionable",
    ):
        assert field_name in prompt


@pytest.mark.parametrize(
    "forbidden",
    [
        _blocked("sta", "ke"),
        _blocked("kel", "ly"),
        _blocked("bank", "roll"),
        _blocked("bet", "_amount"),
        _blocked("wag", "er"),
        _blocked("suggested", "_bet"),
        _blocked("recom", "mended", "_bet"),
        _blocked("exec", "ute"),
        _blocked("exec", "ution"),
        _blocked("place", "_bet"),
        _blocked("entr", "ada"),
        _blocked("ap", "ostar"),
        _blocked("sinal", " de ", "ap", "osta"),
        _blocked("ap", "osta recomen", "dada"),
        _blocked("tele", "gram"),
        _blocked("sched", "uler"),
        _blocked("auto", "evolution"),
    ],
)
def test_prompt_does_not_contain_forbidden_terms(forbidden: str) -> None:
    assert forbidden.lower() not in _prompt().lower()


def test_prompt_declares_simulation_and_paper_trading() -> None:
    prompt = _prompt().lower()

    assert "simulacao" in prompt
    assert "paper trading" in prompt


def test_prompt_declares_not_operational_recommendation() -> None:
    prompt = _prompt().lower()

    assert "nao e recomendacao operacional" in prompt
    assert "nao autoriza acao real" in prompt


def test_prompt_requests_json() -> None:
    prompt = _prompt()

    assert "JSON" in prompt
    assert "apenas JSON" in prompt


def test_prompt_includes_expected_response_fields() -> None:
    prompt = _prompt()

    for field_name in (
        "technical_verdict",
        "confidence",
        "risk_factors",
        "rationale",
    ):
        assert field_name in prompt
    assert "pass" in prompt
    assert "review" in prompt
    assert "reject" in prompt


def test_invalid_object_fails() -> None:
    with pytest.raises(ValueError, match="SafeAIValidationInput"):
        build_gemini_validation_prompt(object())  # type: ignore[arg-type]


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


def test_prompt_module_has_no_network_import_or_call() -> None:
    source = inspect.getsource(validator_module).lower()
    imports = _module_imports()

    assert imports.isdisjoint({"requests", "httpx", "aiohttp", "urllib", "socket"})
    for forbidden in ("urlopen", "request(", ".get(", ".post(", "connect("):
        assert forbidden not in source


def test_prompt_module_has_no_gemini_or_google_import() -> None:
    imports = _module_imports()

    assert "google" not in imports
    assert "genai" not in imports
    assert "generativeai" not in imports


def test_prompt_module_has_no_telegram() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("tele", "gram") not in source


def test_prompt_module_has_no_scheduler() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("sched", "uler") not in source


def test_prompt_module_has_no_auto_evolution() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("auto", "evolution") not in source
    assert _blocked("auto", "_evolution") not in source


def test_prompt_module_has_no_position_sizing_terms() -> None:
    source = inspect.getsource(validator_module).lower()

    assert _blocked("sta", "ke") not in source
    assert _blocked("kel", "ly") not in source
    assert _blocked("bank", "roll") not in source

