"""Tests for STORY-03-009 local ValueDetector sanity check."""

from __future__ import annotations

from pathlib import Path
import inspect

import pytest

from src.edgehunter.core import value_detector_sanity as sanity_module
from src.edgehunter.core.value_detector_sanity import (
    ValueDetectorSanityResult,
    sanity_check_value_detector,
)


def test_sanity_check_returns_structured_success_result() -> None:
    result = sanity_check_value_detector()

    assert isinstance(result, ValueDetectorSanityResult)
    assert result.passed is True
    assert result.reasons == []
    assert result.warnings == ["persistence_checked_with_temporary_sqlite"]
    assert result.metrics["ev_known_case"] is True
    assert result.metrics["opportunity_safety_flags"] is True
    assert result.metrics["pinnacle_invalid_snapshot_skip"] is True
    assert result.metrics["poisson_unready_model_skip"] is True
    assert result.metrics["consensus_divergence_skip"] is True
    assert result.metrics["deduplication_removes_duplicate"] is True
    assert result.metrics["persistence_safety_flags"] is True
    assert result.metrics["operational_guardrails"] is True


def test_sanity_check_can_use_explicit_local_database(tmp_path: Path) -> None:
    db_path = tmp_path / "sanity.db"

    result = sanity_check_value_detector(str(db_path))

    assert result.passed is True
    assert result.warnings == []
    assert db_path.exists()


def test_result_can_be_serialized_to_dict() -> None:
    result = sanity_check_value_detector()

    payload = result.to_dict()

    assert payload["passed"] is True
    assert payload["reasons"] == []
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["metrics"], dict)


def test_sanity_check_reports_failed_known_ev_case(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanity_module, "calculate_ev", lambda true_prob, offered_odds: 0.0)

    result = sanity_check_value_detector()

    assert result.passed is False
    assert "calculate_ev_known_case_failed" in result.reasons
    assert result.metrics["ev_known_case"] is False


def test_sanity_check_reports_failed_runtime_guardrails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sanity_module, "_guardrails_pass", lambda: False)

    result = sanity_check_value_detector()

    assert result.passed is False
    assert "operational_guardrails_failed" in result.reasons
    assert result.metrics["operational_guardrails"] is False


def test_sanity_module_does_not_define_operational_integrations() -> None:
    source = inspect.getsource(sanity_module).lower()

    for forbidden in (
        "telegram",
        "scheduler",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "kelly",
        "bankroll",
        "place_bet",
        "execute_bet",
        "real_money",
    ):
        assert forbidden not in source

    assert "actionable=true" not in source.replace(" ", "")
    assert "bet_placed=true" not in source.replace(" ", "")
    assert "alerted=true" not in source.replace(" ", "")


# --- STORY-04B-001 regression test ---


def test_sanity_deduplication_fixture_uses_dynamic_timestamp() -> None:
    """Regression: _opportunity() must use datetime.now(timezone.utc), not a fixed past
    timestamp. A fixed past timestamp (e.g. '2026-05-28T12:00:00+00:00') falls outside
    the 60-minute deduplication window, so both copies pass through — correct historical
    behaviour but a false-negative in the sanity check.

    This test ensures the sanity check detects real deduplication failures rather than
    silently reporting pass=False due to a stale fixture.
    """
    # A healthy sanity check must confirm deduplication works.
    result = sanity_check_value_detector()

    assert result.metrics["deduplication_removes_duplicate"] is True, (
        "deduplication_removes_duplicate must be True in a healthy environment. "
        "If this fails, check that _opportunity() uses datetime.now(timezone.utc) "
        "for created_at instead of a hardcoded past timestamp."
    )


def test_sanity_deduplication_check_catches_real_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: sanity must report deduplication_removes_duplicate=False when
    deduplicate_opportunities genuinely does not deduplicate.
    """
    from src.edgehunter.core import value_detector_sanity as sm

    # Patch deduplicate_opportunities to never remove anything
    monkeypatch.setattr(sm, "deduplicate_opportunities", lambda opps, **kw: list(opps))

    result = sanity_check_value_detector()

    assert result.passed is False
    assert "logical_deduplication_failed" in result.reasons
    assert result.metrics["deduplication_removes_duplicate"] is False
