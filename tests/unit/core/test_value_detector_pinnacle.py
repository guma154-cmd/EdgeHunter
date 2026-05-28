"""Tests for STORY-03-003 Pinnacle benchmark value detection."""

from __future__ import annotations

import inspect
import math

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    detect_value_vs_pinnacle,
)


def _snapshot(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "snapshot_id": 1,
        "match_id": "match-001",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "league": "Brasileirao",
        "valid_for_analysis": True,
        "odds": {
            "pinnacle": {
                "home": 2.00,
                "draw": 3.20,
                "away": 4.00,
            },
            "bet365": {
                "home": 2.20,
                "draw": 3.10,
                "away": 4.50,
            },
        },
    }
    data.update(overrides)
    return data


def test_detects_simulated_opportunities_when_target_odds_create_positive_ev() -> None:
    opportunities = detect_value_vs_pinnacle(
        _snapshot(),
        target_bookmaker="bet365",
        min_ev=0.0,
    )

    assert [item.selection for item in opportunities] == ["home_win", "away_win"]
    assert opportunities[0].true_probability == pytest.approx(0.5)
    assert opportunities[0].offered_odds == pytest.approx(2.2)
    assert opportunities[0].expected_value == pytest.approx(0.1)
    assert opportunities[1].true_probability == pytest.approx(0.25)
    assert opportunities[1].offered_odds == pytest.approx(4.5)
    assert opportunities[1].expected_value == pytest.approx(0.125)


def test_does_not_detect_when_ev_is_below_minimum_threshold() -> None:
    opportunities = detect_value_vs_pinnacle(
        _snapshot(),
        target_bookmaker="bet365",
        min_ev=0.13,
    )

    assert opportunities == []


def test_invalid_snapshot_does_not_generate_opportunity() -> None:
    opportunities = detect_value_vs_pinnacle(
        _snapshot(valid_for_analysis=False),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_missing_pinnacle_returns_empty_list() -> None:
    snapshot = _snapshot()
    snapshot["odds"] = {"bet365": {"home": 2.2, "draw": 3.1, "away": 4.5}}

    assert detect_value_vs_pinnacle(snapshot, target_bookmaker="bet365") == []


def test_missing_target_bookmaker_returns_empty_list() -> None:
    snapshot = _snapshot()
    snapshot["odds"] = {"pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0}}

    assert detect_value_vs_pinnacle(snapshot, target_bookmaker="bet365") == []


@pytest.mark.parametrize(
    ("bookmaker", "selection", "bad_value"),
    (
        ("pinnacle", "home", 1.0),
        ("pinnacle", "draw", 0.0),
        ("bet365", "away", float("nan")),
        ("bet365", "home", float("inf")),
    ),
)
def test_invalid_odds_fail(bookmaker: str, selection: str, bad_value: float) -> None:
    snapshot = _snapshot()
    snapshot_odds = snapshot["odds"]
    assert isinstance(snapshot_odds, dict)
    bookmaker_odds = snapshot_odds[bookmaker]
    assert isinstance(bookmaker_odds, dict)
    bookmaker_odds[selection] = bad_value

    with pytest.raises(ValueError, match="offered_odds must|must be finite"):
        detect_value_vs_pinnacle(snapshot, target_bookmaker="bet365")


def test_missing_selection_is_not_comparable_and_is_skipped() -> None:
    snapshot = _snapshot()
    snapshot_odds = snapshot["odds"]
    assert isinstance(snapshot_odds, dict)
    bet365_odds = snapshot_odds["bet365"]
    assert isinstance(bet365_odds, dict)
    del bet365_odds["away"]

    opportunities = detect_value_vs_pinnacle(snapshot, target_bookmaker="bet365")

    assert [item.selection for item in opportunities] == ["home_win"]


def test_min_ev_must_be_finite_and_non_negative() -> None:
    with pytest.raises(ValueError, match="min_ev must be finite"):
        detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365", min_ev=float("nan"))

    with pytest.raises(ValueError, match="min_ev must be >= 0"):
        detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365", min_ev=-0.01)


def test_generated_opportunity_uses_simulated_contract_and_safe_flags() -> None:
    opportunity = detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365")[0]

    assert isinstance(opportunity, SimulatedValueOpportunity)
    assert opportunity.is_simulated is True
    assert opportunity.paper_trading is True
    assert opportunity.actionable is False
    assert opportunity.bet_placed is False
    assert opportunity.alerted is False


def test_source_and_detection_method_identify_simulated_pinnacle_benchmark() -> None:
    opportunity = detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365")[0]

    assert opportunity.source == "pinnacle_benchmark"
    assert opportunity.detection_method == "pinnacle_ev_v1"


def test_opportunity_id_is_deterministic() -> None:
    first = detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365")[0]
    second = detect_value_vs_pinnacle(_snapshot(), target_bookmaker="bet365")[0]

    assert first.opportunity_id == second.opportunity_id


def test_pinnacle_detection_module_has_no_position_sizing_fields() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source


def test_pinnacle_detection_module_does_not_persist_or_call_external_services() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "sqlite3" not in source
    assert "value_detections" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source
    assert "scheduler" not in source


def test_pinnacle_detection_module_keeps_future_integrations_out_of_scope() -> None:
    source = inspect.getsource(value_detector_module)

    assert "PoissonModel" not in source
    assert "OddsHistorian" not in source
    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source


def test_pinnacle_detection_module_does_not_implement_real_execution() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "place_bet" not in source
    assert "real_money" not in source
    assert math.isfinite(detect_value_vs_pinnacle(_snapshot(), "bet365")[0].expected_value)
