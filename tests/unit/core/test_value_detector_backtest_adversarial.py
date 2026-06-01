"""Adversarial tests for STORY-04A-006 ValueDetector backtest pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect

import pytest

from src.edgehunter.core import value_detector_backtest as backtest_module
from src.edgehunter.core import value_detector_backtest_dataset as dataset_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    calculate_ev,
)
from src.edgehunter.core.value_detector_backtest import (
    BacktestMetrics,
    BacktestRunResult,
    BacktestSelectionResult,
    calculate_backtest_metrics,
    generate_paper_trading_report,
    run_value_detector_backtest,
)
from src.edgehunter.core.value_detector_backtest_dataset import BacktestHistoricalMatch


NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


class FakeSanityResult:
    passed = True


class FakeModel:
    trained = True

    def __init__(self, probabilities: dict[str, float] | None = None) -> None:
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.20,
            "away_win": 0.20,
        }

    def sanity_check(self) -> FakeSanityResult:
        return FakeSanityResult()

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.4,
            "expected_away_goals": 0.9,
            "used_fallback": False,
        }

    def predict_probabilities(self, *, home_team: str, away_team: str) -> dict[str, float]:
        return self.probabilities


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


def _run_result(selections: list[BacktestSelectionResult] | None = None) -> BacktestRunResult:
    selection_values = selections if selections is not None else [_selection()]
    return BacktestRunResult(
        run_id="run-adversarial",
        started_at=NOW - timedelta(minutes=10),
        finished_at=NOW,
        metrics=calculate_backtest_metrics(
            selection_values,
            total_analyzed=max(1, len(selection_values)),
        ),
        selections=selection_values,
        warnings=("adversarial_fixture",),
        reasons=("guardrail_check",),
    )


def _opportunity(selection: str = "home") -> SimulatedValueOpportunity:
    return SimulatedValueOpportunity(
        match_id="match-001",
        market="1x2",
        selection=selection,
        true_probability=0.60,
        offered_odds=2.00,
        expected_value=0.20,
        edge_percentage=20.0,
        source="adversarial",
        detection_method="manual_fixture",
        created_at=NOW.isoformat(),
    )


def test_empty_dataset_returns_structured_zero_result() -> None:
    result = run_value_detector_backtest([], mode="pinnacle")

    assert result.selections == ()
    assert result.warnings == ("empty_dataset",)
    assert result.reasons == ("no_historical_matches_to_analyze",)
    assert result.metrics.total_analyzed == 0
    assert result.metrics.total_opportunities == 0
    assert result.metrics.hit_rate == 0.0


@pytest.mark.parametrize(
    "odds",
    (
        {},
        {"bet365": {"home": 2.0, "draw": 3.2, "away": 3.5}},
    ),
)
def test_missing_or_incomplete_odds_fail_or_do_not_create_opportunity(
    odds: dict[str, dict[str, float]],
) -> None:
    if not odds:
        with pytest.raises(ValueError, match="odds must include at least one bookmaker"):
            _historical_match(odds=odds)
        return

    result = run_value_detector_backtest(
        [_historical_match(odds=odds)],
        mode="pinnacle",
        target_bookmaker="bet365",
    )

    assert result.selections == ()
    assert result.reasons == ("no_opportunities_detected",)


def test_missing_target_bookmaker_does_not_create_opportunity() -> None:
    result = run_value_detector_backtest(
        [
            _historical_match(
                odds={"pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0}},
            ),
        ],
        mode="pinnacle",
        target_bookmaker="bet365",
    )

    assert result.selections == ()
    assert result.metrics.total_opportunities == 0


def test_missing_real_result_fails_clearly() -> None:
    with pytest.raises(ValueError, match="actual_result must be one"):
        _historical_match(actual_result="")


def test_invalid_snapshot_does_not_create_opportunity() -> None:
    result = run_value_detector_backtest(
        [_historical_match(valid_for_analysis=False)],
        mode="pinnacle",
    )

    assert result.selections == ()
    assert result.metrics.total_analyzed == 1


def test_extreme_high_odds_remain_structured_and_simulated() -> None:
    result = run_value_detector_backtest(
        [
            _historical_match(
                odds={
                    "pinnacle": {"home": 1000.0, "draw": 500.0, "away": 250.0},
                    "bet365": {"home": 1200.0, "draw": 1.01, "away": 1.01},
                },
            ),
        ],
        mode="pinnacle",
        min_ev=0.0,
    )

    assert result.is_simulated is True
    assert result.paper_trading is True
    assert result.actionable is False
    assert all(selection.offered_odds >= 1.01 for selection in result.selections)


def test_extreme_expected_value_contract_remains_finite() -> None:
    selection = _selection(expected_value=999999.0, edge_percentage=99999900.0)
    metrics = calculate_backtest_metrics([selection], total_analyzed=1)

    assert metrics.average_expected_value == pytest.approx(999999.0)
    assert metrics.average_edge_percentage == pytest.approx(99999900.0)


def test_negative_ev_is_filtered_by_detector_minimum() -> None:
    assert calculate_ev(0.10, 2.0) < 0

    result = run_value_detector_backtest(
        [
            _historical_match(
                odds={
                    "pinnacle": {"home": 1.20, "draw": 1.30, "away": 1.40},
                    "bet365": {"home": 1.01, "draw": 1.01, "away": 1.01},
                },
            ),
        ],
        mode="pinnacle",
        min_ev=0.0,
    )

    assert result.selections == ()


def test_very_low_model_probability_does_not_create_value() -> None:
    result = run_value_detector_backtest(
        [
            _historical_match(
                odds={
                    "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
                    "bet365": {"home": 2.0, "draw": 1.01, "away": 1.01},
                },
            ),
        ],
        poisson_model=FakeModel(
            {
                "home_win": 0.000001,
                "draw": 0.499999,
                "away_win": 0.500000,
            },
        ),
        target_bookmaker="bet365",
        mode="poisson",
        min_ev=0.0,
    )

    assert all(selection.selection != "home_win" for selection in result.selections)


@pytest.mark.parametrize("bad_value", (float("nan"), float("inf"), float("-inf")))
def test_nan_and_infinite_odds_fail_controlled(bad_value: float) -> None:
    with pytest.raises(ValueError, match="offered_odds must be finite"):
        run_value_detector_backtest(
            [
                _historical_match(
                    odds={
                        "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
                        "bet365": {"home": bad_value, "draw": 3.0, "away": 3.5},
                    },
                ),
            ],
            mode="pinnacle",
        )


def test_scoreline_divergent_actual_result_fails_clearly() -> None:
    with pytest.raises(ValueError, match="actual_result does not match scoreline"):
        _historical_match(home_goals=2, away_goals=1, actual_result="away_win")


def test_unmapped_selection_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        backtest_module,
        "detect_value_vs_pinnacle",
        lambda *args, **kwargs: [_opportunity("not_a_result")],
    )

    with pytest.raises(ValueError, match="selection cannot be mapped"):
        run_value_detector_backtest([_historical_match()], mode="pinnacle")


def test_unknown_actual_result_fails_clearly() -> None:
    with pytest.raises(ValueError, match="actual_result must be one"):
        _historical_match(actual_result="abandoned")


def test_metrics_total_analyzed_zero_without_opportunities() -> None:
    metrics = calculate_backtest_metrics([], total_analyzed=0)

    assert metrics.total_analyzed == 0
    assert metrics.coverage_rate == 0.0


def test_metrics_all_opportunities_without_hits() -> None:
    metrics = calculate_backtest_metrics(
        [
            _selection(is_hit=False, is_false_positive=True, actual_result="away_win"),
            _selection(
                match_id="match-002",
                is_hit=False,
                is_false_positive=True,
                actual_result="draw",
            ),
        ],
        total_analyzed=2,
    )

    assert metrics.total_hits == 0
    assert metrics.total_false_positives == 2
    assert metrics.false_positive_rate == 1.0


def test_metrics_all_opportunities_hit() -> None:
    metrics = calculate_backtest_metrics(
        [_selection(), _selection(match_id="match-002")],
        total_analyzed=2,
    )

    assert metrics.total_hits == 2
    assert metrics.hit_rate == 1.0


def test_metrics_rejects_hit_and_false_positive_together() -> None:
    with pytest.raises(ValueError, match="cannot be both hit and false positive"):
        calculate_backtest_metrics(
            [_selection(is_hit=True, is_false_positive=True)],
            total_analyzed=1,
        )


def test_metrics_accepts_more_opportunities_than_analyzed_if_same_match() -> None:
    metrics = calculate_backtest_metrics(
        [_selection(match_id="match-001", selection="home_win"), _selection(match_id="match-001", selection="away_win")],
        total_analyzed=1,
    )
    assert metrics.opportunities_per_analyzed_match == 2.0
    assert metrics.coverage_rate == 1.0


def test_groupings_handle_multiple_sources_methods_deterministically() -> None:
    selections = [
        _selection(match_id="match-b", source="z_source", detection_method="z_method"),
        _selection(match_id="match-a", source="a_source", detection_method="a_method"),
        _selection(match_id="match-m", source="m_source", detection_method="m_method"),
    ]

    first = calculate_backtest_metrics(selections, total_analyzed=3)
    second = calculate_backtest_metrics(selections, total_analyzed=3)

    assert list(first.by_source) == ["a_source", "m_source", "z_source"]
    assert list(first.by_detection_method) == ["a_method", "m_method", "z_method"]
    assert first.to_dict() == second.to_dict()


def test_empty_source_and_detection_method_fail_clearly() -> None:
    with pytest.raises(ValueError, match="source is required"):
        _selection(source="")
    with pytest.raises(ValueError, match="detection_method is required"):
        _selection(detection_method="")


def test_report_without_selections_is_structured() -> None:
    result = BacktestRunResult(
        run_id="empty-report",
        started_at=NOW - timedelta(minutes=1),
        finished_at=NOW,
        metrics=calculate_backtest_metrics([], total_analyzed=0),
        selections=(),
        warnings=("empty_dataset",),
        reasons=("no_historical_matches_to_analyze",),
    )

    report = generate_paper_trading_report(result, format="dict")

    assert report["selection_sample"] == []
    assert report["total_selections"] == 0
    assert report["metrics"]["total_opportunities"] == 0


def test_report_many_selections_limits_sample_and_is_deterministic() -> None:
    selections = [
        _selection(match_id=f"match-{index:03d}")
        for index in range(10)
    ]
    result = _run_result(selections)

    first = generate_paper_trading_report(result, format="markdown")
    second = generate_paper_trading_report(result, format="markdown")
    payload = generate_paper_trading_report(result, format="dict")

    assert first == second
    assert payload["selection_sample_limit"] == 5
    assert len(payload["selection_sample"]) == 5


def test_report_has_no_operational_language() -> None:
    report = generate_paper_trading_report(_run_result(), format="markdown").lower()

    for forbidden in (
        "clique",
        "entre agora",
        "sinal ao vivo",
        "sta" + "ke",
        "kel" + "ly",
        "bank" + "roll",
        "place_" + "bet",
        "execute_" + "bet",
        "real_" + "money",
    ):
        assert forbidden not in report


def test_safety_flags_cannot_be_enabled() -> None:
    with pytest.raises(ValueError, match="actionable must be False"):
        _selection(actionable=True)
    with pytest.raises(ValueError, match="bet_placed must be False"):
        _selection(bet_placed=True)
    with pytest.raises(ValueError, match="alerted must be False"):
        _selection(alerted=True)


def test_backtest_core_has_no_operational_integrations() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "sqlite3",
        "get_backtest_dataset",
        "db_path",
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
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


def test_dataset_module_guardrails_remain_narrow() -> None:
    source = inspect.getsource(dataset_module).lower()

    for forbidden in (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
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
    ):
        assert forbidden not in source
