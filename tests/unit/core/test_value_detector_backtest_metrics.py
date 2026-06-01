"""Tests for STORY-04A-004 ValueDetector backtest quality metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect
import math

import pytest

from src.edgehunter.core import value_detector_backtest as backtest_module
from src.edgehunter.core.value_detector import SimulatedValueOpportunity
from src.edgehunter.core.value_detector_backtest import (
    BacktestSelectionResult,
    calculate_backtest_metrics,
    run_value_detector_backtest,
)
from src.edgehunter.core.value_detector_backtest_dataset import BacktestHistoricalMatch


NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _selection(**overrides: object) -> BacktestSelectionResult:
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home",
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


def _historical_match(**overrides: object) -> BacktestHistoricalMatch:
    data: dict[str, object] = {
        "match_id": "match-001",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "league": "Brasileirao",
        "scheduled_time": NOW - timedelta(hours=2),
        "home_goals": 2,
        "away_goals": 1,
        "actual_result": "home_win",
        "snapshot_id": 1,
        "snapshot_timestamp": NOW - timedelta(hours=3),
        "valid_for_analysis": True,
        "odds": {
            "pinnacle": {"home": 2.00, "draw": 3.20, "away": 4.00},
            "bet365": {"home": 2.20, "draw": 3.00, "away": 3.50},
        },
    }
    data.update(overrides)
    return BacktestHistoricalMatch(**data)


def _simulated_opportunity() -> SimulatedValueOpportunity:
    return SimulatedValueOpportunity(
        match_id="match-001",
        market="1x2",
        selection="home",
        true_probability=0.60,
        offered_odds=2.00,
        expected_value=0.20,
        edge_percentage=20.0,
        source="unit-test",
        detection_method="centralized-metrics-test",
        created_at=NOW.isoformat(),
    )


def _corrupt_selection(
    field_name: str,
    value: object,
    **overrides: object,
) -> BacktestSelectionResult:
    selection = _selection(**overrides)
    object.__setattr__(selection, field_name, value)
    return selection


def test_calculates_metrics_with_opportunities_and_hits() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001"),
            _selection(match_id="match-002", expected_value=0.10, edge_percentage=10.0),
        ],
        total_analyzed=4,
    )

    assert metrics.total_analyzed == 4
    assert metrics.total_opportunities == 2
    assert metrics.total_hits == 2
    assert metrics.total_false_positives == 0
    assert metrics.hit_rate == pytest.approx(1.0)
    assert metrics.false_positive_rate == pytest.approx(0.0)


def test_calculates_metrics_with_false_positive() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(is_hit=False, is_false_positive=True, actual_result="away_win"),
        ],
        total_analyzed=2,
    )

    assert metrics.total_opportunities == 1
    assert metrics.total_hits == 0
    assert metrics.total_false_positives == 1
    assert metrics.hit_rate == pytest.approx(0.0)
    assert metrics.false_positive_rate == pytest.approx(1.0)


def test_calculates_metrics_without_opportunities() -> None:
    metrics = calculate_backtest_metrics([], total_analyzed=3)

    assert metrics.total_analyzed == 3
    assert metrics.total_opportunities == 0
    assert metrics.total_hits == 0
    assert metrics.total_false_positives == 0
    assert metrics.hit_rate == pytest.approx(0.0)
    assert metrics.false_positive_rate == pytest.approx(0.0)
    assert metrics.average_expected_value == pytest.approx(0.0)
    assert metrics.average_edge_percentage == pytest.approx(0.0)
    assert metrics.by_source == {}
    assert metrics.by_detection_method == {}


def test_calculates_coverage_rate() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001"),
            _selection(match_id="match-002", expected_value=0.10, edge_percentage=10.0),
        ],
        total_analyzed=5,
    )

    assert metrics.coverage_rate == pytest.approx(0.4)


def test_total_analyzed_zero_does_not_break_without_opportunities() -> None:
    metrics = calculate_backtest_metrics([], total_analyzed=0)

    assert metrics.total_analyzed == 0
    assert metrics.coverage_rate == pytest.approx(0.0)


def test_calculates_average_expected_value() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(expected_value=0.10),
            _selection(match_id="match-002", expected_value=0.30),
        ],
        total_analyzed=2,
    )

    assert metrics.average_expected_value == pytest.approx(0.20)


def test_calculates_average_edge_percentage() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(edge_percentage=10.0),
            _selection(match_id="match-002", edge_percentage=30.0),
        ],
        total_analyzed=2,
    )

    assert metrics.average_edge_percentage == pytest.approx(20.0)


def test_groups_metrics_by_source() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001", source="pinnacle_benchmark"),
            _selection(
                match_id="match-002",
                source="pinnacle_benchmark",
                expected_value=0.10,
                edge_percentage=10.0,
                is_hit=False,
                is_false_positive=True,
                actual_result="away_win",
            ),
            _selection(
                match_id="match-003",
                source="poisson_model",
                detection_method="poisson_ev_v1",
                expected_value=0.30,
                edge_percentage=30.0,
            ),
        ],
        total_analyzed=3,
    )

    pinnacle = metrics.by_source["pinnacle_benchmark"]
    assert pinnacle["total_opportunities"] == 2
    assert pinnacle["total_hits"] == 1
    assert pinnacle["total_false_positives"] == 1
    assert pinnacle["hit_rate"] == pytest.approx(0.5)
    assert pinnacle["false_positive_rate"] == pytest.approx(0.5)
    assert pinnacle["average_expected_value"] == pytest.approx(0.15)
    assert pinnacle["average_edge_percentage"] == pytest.approx(15.0)
    assert pinnacle["opportunities"] == 2
    assert pinnacle["hits"] == 1


def test_groups_metrics_by_detection_method() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001", detection_method="pinnacle_ev_v1"),
            _selection(
                match_id="match-002",
                detection_method="pinnacle_ev_v1",
                expected_value=0.10,
                edge_percentage=10.0,
                is_hit=False,
                is_false_positive=True,
                actual_result="away_win",
            ),
            _selection(
                match_id="match-003",
                source="consensus",
                detection_method="consensus_ev_v1",
                expected_value=0.40,
                edge_percentage=40.0,
            ),
        ],
        total_analyzed=3,
    )

    pinnacle = metrics.by_detection_method["pinnacle_ev_v1"]
    assert pinnacle["total_opportunities"] == 2
    assert pinnacle["total_hits"] == 1
    assert pinnacle["total_false_positives"] == 1
    assert pinnacle["hit_rate"] == pytest.approx(0.5)
    assert pinnacle["false_positive_rate"] == pytest.approx(0.5)
    assert pinnacle["average_expected_value"] == pytest.approx(0.15)
    assert pinnacle["average_edge_percentage"] == pytest.approx(15.0)
    assert pinnacle["false_positives"] == 1


def test_total_analyzed_below_zero_fails() -> None:
    with pytest.raises(ValueError, match="total_analyzed must be >= 0"):
        calculate_backtest_metrics([], total_analyzed=-1)


def test_more_opportunities_than_analyzed_does_not_fail() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001", selection="home_win"),
            _selection(match_id="match-001", selection="away_win"),
        ],
        total_analyzed=1,
    )
    assert metrics.opportunities_per_analyzed_match == 2.0
    assert metrics.coverage_rate == 1.0


def test_selection_cannot_be_hit_and_false_positive_at_same_time() -> None:
    with pytest.raises(ValueError, match="cannot be both hit and false positive"):
        calculate_backtest_metrics(
            [_selection(is_hit=True, is_false_positive=True)],
            total_analyzed=1,
        )


@pytest.mark.parametrize("bad_value", (float("nan"), float("inf"), float("-inf")))
def test_nan_and_infinite_expected_value_fail(bad_value: float) -> None:
    with pytest.raises(ValueError, match="expected_value must be finite"):
        calculate_backtest_metrics(
            [_corrupt_selection("expected_value", bad_value)],
            total_analyzed=1,
        )


@pytest.mark.parametrize("bad_value", (float("nan"), float("inf"), float("-inf")))
def test_nan_and_infinite_edge_percentage_fail(bad_value: float) -> None:
    with pytest.raises(ValueError, match="edge_percentage must be finite"):
        calculate_backtest_metrics(
            [_corrupt_selection("edge_percentage", bad_value)],
            total_analyzed=1,
        )


def test_rates_stay_inside_closed_unit_interval() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(match_id="match-001"),
            _selection(
                match_id="match-002",
                source="poisson_model",
                detection_method="poisson_ev_v1",
                is_hit=False,
                is_false_positive=True,
                actual_result="away_win",
            ),
        ],
        total_analyzed=4,
    )

    assert 0.0 <= metrics.hit_rate <= 1.0
    assert 0.0 <= metrics.false_positive_rate <= 1.0
    assert 0.0 <= metrics.coverage_rate <= 1.0
    for grouped_metrics in (
        *metrics.by_source.values(),
        *metrics.by_detection_method.values(),
    ):
        assert 0.0 <= grouped_metrics["hit_rate"] <= 1.0
        assert 0.0 <= grouped_metrics["false_positive_rate"] <= 1.0


def test_executor_uses_centralized_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_calculator = backtest_module.calculate_backtest_metrics
    calls: list[tuple[tuple[BacktestSelectionResult, ...], int]] = []

    def spy_calculator(
        selections: list[BacktestSelectionResult] | tuple[BacktestSelectionResult, ...],
        total_analyzed: int,
    ):
        calls.append((tuple(selections), total_analyzed))
        return original_calculator(selections, total_analyzed)

    monkeypatch.setattr(backtest_module, "calculate_backtest_metrics", spy_calculator)
    monkeypatch.setattr(
        backtest_module,
        "detect_value_vs_pinnacle",
        lambda *args, **kwargs: [_simulated_opportunity()],
    )

    result = run_value_detector_backtest([_historical_match()], mode="pinnacle")

    assert len(calls) == 1
    assert calls[0][1] == 1
    assert len(calls[0][0]) == 1
    assert result.metrics.total_opportunities == 1


def test_metrics_module_does_not_query_sqlite_or_dataset_loader() -> None:
    source = inspect.getsource(backtest_module)

    assert "sqlite3" not in source
    assert "get_backtest_dataset" not in source
    assert "db_path" not in source


def test_metrics_module_does_not_use_network_message_or_timing_services() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
    ):
        assert forbidden not in source


def test_metrics_module_does_not_implement_public_interface_or_execution() -> None:
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


def test_numeric_outputs_are_finite() -> None:
    metrics = calculate_backtest_metrics([_selection()], total_analyzed=1)

    assert math.isfinite(metrics.average_expected_value)
    assert math.isfinite(metrics.average_edge_percentage)
    assert math.isfinite(metrics.by_source["pinnacle_benchmark"]["hit_rate"])
