"""Tests for STORY-04A-001 ValueDetector backtest result contracts."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
import inspect
import math

import pytest

from src.edgehunter.core import value_detector_backtest as backtest_module
from src.edgehunter.core.value_detector_backtest import (
    BacktestMetrics,
    BacktestRunResult,
    BacktestSelectionResult,
)


NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _selection(**overrides: object) -> BacktestSelectionResult:
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home_win",
        "source": "pinnacle_benchmark",
        "detection_method": "pinnacle_ev_v1",
        "predicted_probability": 0.60,
        "offered_odds": 2.0,
        "expected_value": 0.20,
        "edge_percentage": 20.0,
        "actual_result": "home_win",
        "is_hit": True,
        "is_false_positive": False,
        "evaluated_at": NOW,
    }
    data.update(overrides)
    return BacktestSelectionResult(**data)


def _metrics(**overrides: object) -> BacktestMetrics:
    data: dict[str, object] = {
        "total_analyzed": 10,
        "total_opportunities": 2,
        "total_hits": 1,
        "total_false_positives": 1,
        "hit_rate": 0.5,
        "false_positive_rate": 0.5,
        "coverage_rate": 0.2,
        "opportunities_per_analyzed_match": 0.2,
        "average_expected_value": 0.12,
        "average_edge_percentage": 12.0,
        "by_source": {"pinnacle_benchmark": {"opportunities": 2, "hits": 1}},
        "by_detection_method": {"pinnacle_ev_v1": {"opportunities": 2, "hits": 1}},
    }
    data.update(overrides)
    return BacktestMetrics(**data)


def _run(**overrides: object) -> BacktestRunResult:
    data: dict[str, object] = {
        "run_id": "run-001",
        "started_at": NOW - timedelta(minutes=1),
        "finished_at": NOW,
        "metrics": _metrics(),
        "selections": [_selection()],
        "warnings": ["synthetic_fixture"],
        "reasons": ["contract_only"],
    }
    data.update(overrides)
    return BacktestRunResult(**data)


def test_creates_valid_backtest_selection_result() -> None:
    selection = _selection()

    assert selection.match_id == "match-001"
    assert selection.market == "1x2"
    assert selection.selection == "home_win"
    assert selection.source == "pinnacle_benchmark"
    assert selection.detection_method == "pinnacle_ev_v1"
    assert selection.predicted_probability == pytest.approx(0.60)
    assert selection.offered_odds == pytest.approx(2.0)
    assert selection.expected_value == pytest.approx(0.20)
    assert selection.edge_percentage == pytest.approx(20.0)
    assert selection.actual_result == "home_win"
    assert selection.is_hit is True
    assert selection.is_false_positive is False
    assert selection.evaluated_at == NOW


def test_creates_valid_backtest_metrics() -> None:
    metrics = _metrics()

    assert metrics.total_analyzed == 10
    assert metrics.total_opportunities == 2
    assert metrics.total_hits == 1
    assert metrics.total_false_positives == 1
    assert metrics.hit_rate == pytest.approx(0.5)
    assert metrics.false_positive_rate == pytest.approx(0.5)
    assert metrics.coverage_rate == pytest.approx(0.2)
    assert metrics.opportunities_per_analyzed_match == pytest.approx(0.2)
    assert metrics.average_expected_value == pytest.approx(0.12)
    assert metrics.average_edge_percentage == pytest.approx(12.0)
    assert metrics.by_source == {"pinnacle_benchmark": {"opportunities": 2, "hits": 1}}
    assert metrics.by_detection_method == {"pinnacle_ev_v1": {"opportunities": 2, "hits": 1}}


def test_creates_valid_backtest_run_result() -> None:
    run = _run()

    assert run.run_id == "run-001"
    assert run.started_at == NOW - timedelta(minutes=1)
    assert run.finished_at == NOW
    assert run.metrics == _metrics()
    assert run.selections == (_selection(),)
    assert run.warnings == ("synthetic_fixture",)
    assert run.reasons == ("contract_only",)


def test_to_dict_is_deterministic() -> None:
    first = _run().to_dict()
    second = _run().to_dict()

    assert first == second
    assert list(first) == [
        "run_id",
        "started_at",
        "finished_at",
        "metrics",
        "selections",
        "warnings",
        "reasons",
        "is_simulated",
        "paper_trading",
        "actionable",
    ]
    assert first["started_at"] == "2026-05-31T11:59:00+00:00"
    assert first["finished_at"] == "2026-05-31T12:00:00+00:00"


def test_selection_to_dict_preserves_safety_flags() -> None:
    payload = _selection().to_dict()

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False


def test_run_to_dict_preserves_safety_flags() -> None:
    payload = _run().to_dict()

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False
    assert payload["selections"][0]["bet_placed"] is False
    assert payload["selections"][0]["alerted"] is False


@pytest.mark.parametrize(
    ("factory", "field_name"),
    (
        (_selection, "predicted_probability"),
        (_selection, "offered_odds"),
        (_selection, "expected_value"),
        (_selection, "edge_percentage"),
        (_metrics, "hit_rate"),
        (_metrics, "false_positive_rate"),
        (_metrics, "coverage_rate"),
        (_metrics, "opportunities_per_analyzed_match"),
        (_metrics, "average_expected_value"),
        (_metrics, "average_edge_percentage"),
    ),
)
@pytest.mark.parametrize("bad_value", (float("nan"), float("inf"), float("-inf")))
def test_nan_and_infinite_values_are_rejected(
    factory: object,
    field_name: str,
    bad_value: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        factory(**{field_name: bad_value})  # type: ignore[operator]


@pytest.mark.parametrize("predicted_probability", (-0.01, 1.01))
def test_invalid_probability_fails(predicted_probability: float) -> None:
    with pytest.raises(ValueError, match="predicted_probability must be between 0 and 1"):
        _selection(predicted_probability=predicted_probability)


@pytest.mark.parametrize("offered_odds", (0.0, 1.0, 1.009))
def test_invalid_odds_fails(offered_odds: float) -> None:
    with pytest.raises(ValueError, match="offered_odds must be >= 1.01"):
        _selection(offered_odds=offered_odds)


@pytest.mark.parametrize(
    ("factory", "field_name"),
    (
        (_selection, "evaluated_at"),
        (_run, "started_at"),
        (_run, "finished_at"),
    ),
)
def test_naive_timestamps_fail(factory: object, field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be timezone-aware"):
        factory(**{field_name: datetime(2026, 5, 31, 12, 0)})  # type: ignore[operator]


@pytest.mark.parametrize(
    "field_name",
    (
        "total_analyzed",
        "total_opportunities",
        "total_hits",
        "total_false_positives",
    ),
)
def test_negative_counters_fail(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be >= 0"):
        _metrics(**{field_name: -1})


@pytest.mark.parametrize("field_name", ("hit_rate", "false_positive_rate", "coverage_rate"))
@pytest.mark.parametrize("bad_value", (-0.01, 1.01))
def test_rates_outside_closed_unit_interval_fail(field_name: str, bad_value: float) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be between 0 and 1"):
        _metrics(**{field_name: bad_value})


@pytest.mark.parametrize(
    ("factory", "field_name", "unsafe_value", "message"),
    (
        (_selection, "is_simulated", False, "is_simulated must be True"),
        (_selection, "paper_trading", False, "paper_trading must be True"),
        (_selection, "actionable", True, "actionable must be False"),
        (_selection, "bet_placed", True, "bet_placed must be False"),
        (_selection, "alerted", True, "alerted must be False"),
        (_run, "is_simulated", False, "is_simulated must be True"),
        (_run, "paper_trading", False, "paper_trading must be True"),
        (_run, "actionable", True, "actionable must be False"),
    ),
)
def test_safety_flags_cannot_be_overridden(
    factory: object,
    field_name: str,
    unsafe_value: bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory(**{field_name: unsafe_value})  # type: ignore[operator]


def test_contract_has_no_position_sizing_fields() -> None:
    all_field_names = {
        field.name.lower()
        for contract in (BacktestSelectionResult, BacktestMetrics, BacktestRunResult)
        for field in fields(contract)
    }

    assert not any("sta" + "ke" in field_name for field_name in all_field_names)
    assert not any("kel" + "ly" in field_name for field_name in all_field_names)
    assert not any("bank" + "roll" in field_name for field_name in all_field_names)


def test_module_does_not_access_sqlite_network_or_message_services() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "sqlite3",
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
    ):
        assert forbidden not in source


def test_module_does_not_implement_public_interface_or_financial_execution() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "fastapi",
        "flask",
        "endpoint",
        "route",
        "sta" + "ke",
        "kel" + "ly",
        "bank" + "roll",
        "place_" + "bet",
        "execute_" + "bet",
        "real_" + "money",
        "geminivalidator",
        "autoevolution",
    ):
        assert forbidden not in source


def test_numeric_values_remain_finite() -> None:
    selection = _selection()
    metrics = _metrics()

    assert math.isfinite(selection.predicted_probability)
    assert math.isfinite(selection.offered_odds)
    assert math.isfinite(selection.expected_value)
    assert math.isfinite(selection.edge_percentage)
    assert math.isfinite(metrics.average_expected_value)
    assert math.isfinite(metrics.average_edge_percentage)
