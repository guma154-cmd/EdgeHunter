"""Tests for STORY-03-006 local simulated opportunity deduplication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    deduplicate_opportunities,
)


NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _opportunity(**overrides: object) -> SimulatedValueOpportunity:
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.60,
        "offered_odds": 2.00,
        "expected_value": 0.20,
        "edge_percentage": 20.0,
        "source": "consensus",
        "detection_method": "consensus_pinnacle_poisson_v1",
        "created_at": (NOW - timedelta(minutes=5)).isoformat(),
    }
    data.update(overrides)
    return SimulatedValueOpportunity(**data)


def test_returns_unique_opportunities() -> None:
    first = _opportunity(match_id="match-001")
    second = _opportunity(match_id="match-002")

    result = deduplicate_opportunities([first, second], now=NOW)

    assert result == [first, second]


def test_removes_duplicate_inside_same_list_and_preserves_first_occurrence() -> None:
    first = _opportunity(offered_odds=2.00, expected_value=0.20)
    duplicate = _opportunity(offered_odds=2.10, expected_value=0.26)

    result = deduplicate_opportunities([first, duplicate], now=NOW)

    assert result == [first]


def test_removes_duplicate_present_in_seen() -> None:
    seen = [_opportunity(created_at=(NOW - timedelta(minutes=10)).isoformat())]
    current = _opportunity(created_at=(NOW - timedelta(minutes=5)).isoformat())

    result = deduplicate_opportunities([current], seen=seen, now=NOW)

    assert result == []


def test_seen_can_be_dictionary_payload() -> None:
    seen = [
        _opportunity(created_at=(NOW - timedelta(minutes=10)).isoformat()).to_dict()
    ]
    current = _opportunity(created_at=(NOW - timedelta(minutes=5)).isoformat())

    result = deduplicate_opportunities([current], seen=seen, now=NOW)

    assert result == []


def test_does_not_remove_opportunity_outside_window() -> None:
    seen = [_opportunity(created_at=(NOW - timedelta(minutes=61)).isoformat())]
    current = _opportunity(created_at=(NOW - timedelta(minutes=5)).isoformat())

    result = deduplicate_opportunities([current], seen=seen, window_minutes=60, now=NOW)

    assert result == [current]


def test_does_not_remove_different_selection() -> None:
    first = _opportunity(selection="home_win")
    second = _opportunity(selection="away_win")

    assert deduplicate_opportunities([first, second], now=NOW) == [first, second]


def test_does_not_remove_different_market() -> None:
    first = _opportunity(market="1x2")
    second = _opportunity(market="totals")

    assert deduplicate_opportunities([first, second], now=NOW) == [first, second]


def test_does_not_remove_different_match_id() -> None:
    first = _opportunity(match_id="match-001")
    second = _opportunity(match_id="match-002")

    assert deduplicate_opportunities([first, second], now=NOW) == [first, second]


def test_does_not_remove_different_source_or_detection_method() -> None:
    first = _opportunity(source="pinnacle_benchmark", detection_method="pinnacle_ev_v1")
    second = _opportunity(source="poisson_model", detection_method="poisson_ev_v1")

    assert deduplicate_opportunities([first, second], now=NOW) == [first, second]


@pytest.mark.parametrize("window_minutes", (0, -1))
def test_window_minutes_must_be_positive(window_minutes: int) -> None:
    with pytest.raises(ValueError, match="window_minutes must be > 0"):
        deduplicate_opportunities(
            [_opportunity()],
            window_minutes=window_minutes,
            now=NOW,
        )


def test_now_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        deduplicate_opportunities([_opportunity()], now=datetime(2026, 5, 28, 12, 0))


def test_preserves_security_flags() -> None:
    result = deduplicate_opportunities([_opportunity()], now=NOW)

    assert result[0].is_simulated is True
    assert result[0].paper_trading is True
    assert result[0].actionable is False
    assert result[0].bet_placed is False
    assert result[0].alerted is False


def test_does_not_use_opportunity_id_as_only_key() -> None:
    first = _opportunity(offered_odds=2.00, expected_value=0.20)
    second = _opportunity(offered_odds=2.20, expected_value=0.32)

    assert first.opportunity_id != second.opportunity_id
    assert deduplicate_opportunities([first, second], now=NOW) == [first]


def test_material_odds_change_does_not_prevent_logical_deduplication_inside_window() -> None:
    seen = [_opportunity(offered_odds=2.00, expected_value=0.20)]
    current = _opportunity(offered_odds=2.50, expected_value=0.50)

    assert current.opportunity_id != seen[0].opportunity_id
    assert deduplicate_opportunities([current], seen=seen, now=NOW) == []


def test_rejects_unsafe_opportunity_shape() -> None:
    unsafe = object.__new__(SimulatedValueOpportunity)
    object.__setattr__(unsafe, "match_id", "match-001")
    object.__setattr__(unsafe, "market", "1x2")
    object.__setattr__(unsafe, "selection", "home_win")
    object.__setattr__(unsafe, "source", "consensus")
    object.__setattr__(unsafe, "detection_method", "consensus_pinnacle_poisson_v1")
    object.__setattr__(unsafe, "created_at", NOW.isoformat())
    object.__setattr__(unsafe, "is_simulated", False)
    object.__setattr__(unsafe, "paper_trading", True)
    object.__setattr__(unsafe, "actionable", False)
    object.__setattr__(unsafe, "bet_placed", False)
    object.__setattr__(unsafe, "alerted", False)

    with pytest.raises(ValueError, match="opportunity must be simulated"):
        deduplicate_opportunities([unsafe], now=NOW)


def test_deduplication_module_does_not_persist_or_access_sqlite() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "sqlite3" not in source
    assert "value_detections" not in source


def test_deduplication_module_does_not_call_external_services() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source
    assert "scheduler" not in source


def test_deduplication_module_does_not_implement_financial_execution() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source
    assert "place_bet" not in source
    assert "real_money" not in source
