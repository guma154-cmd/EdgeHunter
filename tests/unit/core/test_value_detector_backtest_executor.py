"""Tests for STORY-04A-003 pure ValueDetector backtest executor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import inspect

import pytest

from src.edgehunter.core import value_detector_backtest as backtest_module
from src.edgehunter.core.value_detector import SimulatedValueOpportunity
from src.edgehunter.core.value_detector_backtest import (
    BacktestRunResult,
    run_value_detector_backtest,
)
from src.edgehunter.core.value_detector_backtest_dataset import BacktestHistoricalMatch


NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class FakeSanityResult:
    passed: bool


class FakeModel:
    def __init__(
        self,
        *,
        trained: bool = True,
        sanity_passed: bool = True,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        self.trained = trained
        self.sanity_passed = sanity_passed
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.20,
            "away_win": 0.20,
        }

    def sanity_check(self) -> FakeSanityResult:
        return FakeSanityResult(passed=self.sanity_passed)

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.5,
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


def _simulated_opportunity(selection: str) -> SimulatedValueOpportunity:
    return SimulatedValueOpportunity(
        match_id="match-001",
        market="1x2",
        selection=selection,
        true_probability=0.60,
        offered_odds=2.00,
        expected_value=0.20,
        edge_percentage=20.0,
        source="unit-test",
        detection_method="mapping-test",
        created_at=NOW.isoformat(),
    )


def test_runs_backtest_in_pinnacle_mode() -> None:
    result = run_value_detector_backtest(
        [_historical_match()],
        mode="pinnacle",
        target_bookmaker="bet365",
    )

    assert isinstance(result, BacktestRunResult)
    assert len(result.selections) == 1
    assert result.selections[0].source == "pinnacle_benchmark"
    assert result.metrics.total_analyzed == 1
    assert result.metrics.total_opportunities == 1


def test_runs_backtest_in_poisson_mode() -> None:
    result = run_value_detector_backtest(
        [_historical_match()],
        poisson_model=FakeModel(),
        mode="poisson",
        target_bookmaker="bet365",
    )

    assert len(result.selections) == 1
    assert result.selections[0].source == "poisson_model"
    assert result.selections[0].expected_value == pytest.approx(0.32)


def test_runs_backtest_in_consensus_mode() -> None:
    result = run_value_detector_backtest(
        [_historical_match()],
        poisson_model=FakeModel(),
        mode="consensus",
        target_bookmaker="bet365",
    )

    assert len(result.selections) == 1
    assert result.selections[0].source == "consensus"
    assert result.selections[0].expected_value == pytest.approx(0.10)


def test_unknown_mode_fails_clearly() -> None:
    with pytest.raises(ValueError, match="unsupported backtest mode"):
        run_value_detector_backtest([_historical_match()], mode="unknown")


def test_empty_dataset_returns_structured_result_with_warning_and_reason() -> None:
    result = run_value_detector_backtest([], mode="pinnacle")

    assert isinstance(result, BacktestRunResult)
    assert result.selections == ()
    assert result.metrics.total_analyzed == 0
    assert result.metrics.total_opportunities == 0
    assert result.warnings == ("empty_dataset",)
    assert result.reasons == ("no_historical_matches_to_analyze",)


def test_detected_opportunity_with_correct_result_is_hit() -> None:
    result = run_value_detector_backtest(
        [_historical_match(actual_result="home_win")],
        mode="pinnacle",
    )

    assert result.selections[0].is_hit is True
    assert result.selections[0].is_false_positive is False
    assert result.metrics.total_hits == 1
    assert result.metrics.total_false_positives == 0


def test_detected_opportunity_with_wrong_result_is_false_positive() -> None:
    result = run_value_detector_backtest(
        [
            _historical_match(
                home_goals=0,
                away_goals=1,
                actual_result="away_win",
            ),
        ],
        mode="pinnacle",
    )

    assert result.selections[0].is_hit is False
    assert result.selections[0].is_false_positive is True
    assert result.metrics.total_hits == 0
    assert result.metrics.total_false_positives == 1


@pytest.mark.parametrize(
    ("selection", "actual_result", "home_goals", "away_goals"),
    (
        ("home", "home_win", 2, 1),
        ("draw", "draw", 1, 1),
        ("away", "away_win", 0, 1),
    ),
)
def test_selection_alias_maps_to_actual_result(
    monkeypatch: pytest.MonkeyPatch,
    selection: str,
    actual_result: str,
    home_goals: int,
    away_goals: int,
) -> None:
    monkeypatch.setattr(
        backtest_module,
        "detect_value_vs_pinnacle",
        lambda *args, **kwargs: [_simulated_opportunity(selection)],
    )

    result = run_value_detector_backtest(
        [
            _historical_match(
                home_goals=home_goals,
                away_goals=away_goals,
                actual_result=actual_result,
            ),
        ],
        mode="pinnacle",
    )

    assert result.selections[0].is_hit is True


def test_unknown_selection_mapping_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        backtest_module,
        "detect_value_vs_pinnacle",
        lambda *args, **kwargs: [_simulated_opportunity("not_a_result")],
    )

    with pytest.raises(ValueError, match="selection cannot be mapped"):
        run_value_detector_backtest([_historical_match()], mode="pinnacle")


def test_security_flags_are_preserved() -> None:
    result = run_value_detector_backtest([_historical_match()], mode="pinnacle")
    payload = result.to_dict()

    assert result.is_simulated is True
    assert result.paper_trading is True
    assert result.actionable is False
    assert result.selections[0].is_simulated is True
    assert result.selections[0].paper_trading is True
    assert result.selections[0].actionable is False
    assert result.selections[0].bet_placed is False
    assert result.selections[0].alerted is False
    assert payload["selections"][0]["bet_placed"] is False
    assert payload["selections"][0]["alerted"] is False


def test_basic_metrics_are_filled() -> None:
    result = run_value_detector_backtest(
        [
            _historical_match(match_id="match-001", actual_result="home_win"),
            _historical_match(
                match_id="match-002",
                home_goals=0,
                away_goals=1,
                actual_result="away_win",
            ),
        ],
        mode="pinnacle",
    )

    assert result.metrics.total_analyzed == 2
    assert result.metrics.total_opportunities == 2
    assert result.metrics.total_hits == 1
    assert result.metrics.total_false_positives == 1
    assert result.metrics.hit_rate == pytest.approx(0.5)
    assert result.metrics.false_positive_rate == pytest.approx(0.5)
    assert result.metrics.coverage_rate == pytest.approx(1.0)
    assert result.metrics.average_expected_value == pytest.approx(0.1)
    assert result.metrics.average_edge_percentage == pytest.approx(10.0)
    assert result.metrics.by_source["pinnacle_benchmark"]["opportunities"] == 2
    assert result.metrics.by_detection_method["pinnacle_ev_v1"]["hits"] == 1


def test_no_opportunities_records_insufficient_data_reason() -> None:
    result = run_value_detector_backtest(
        [_historical_match(valid_for_analysis=False)],
        mode="pinnacle",
    )

    assert result.selections == ()
    assert result.metrics.total_analyzed == 1
    assert result.reasons == ("no_opportunities_detected",)


def test_backtest_executor_does_not_query_sqlite_or_get_dataset() -> None:
    source = inspect.getsource(backtest_module)

    assert "sqlite3" not in source
    assert "get_backtest_dataset" not in source
    assert "db_path" not in source


def test_backtest_executor_does_not_persist_or_call_external_services() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "value_detections",
        "persist_simulated_opportunities",
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
    ):
        assert forbidden not in source


def test_backtest_executor_does_not_implement_financial_or_real_execution() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "sta" + "ke",
        "kel" + "ly",
        "bank" + "roll",
        "place_" + "bet",
        "execute_" + "bet",
        "real_" + "money",
    ):
        assert forbidden not in source
