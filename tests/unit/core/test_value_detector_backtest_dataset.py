"""Tests for STORY-04A-002 local historical backtest dataset."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
import inspect
import sqlite3
import tempfile

import pytest

from src.edgehunter.core import value_detector_backtest_dataset as dataset_module
from src.edgehunter.core.odds_historian import OddsHistorian
from src.edgehunter.core.value_detector_backtest_dataset import (
    BacktestHistoricalMatch,
    get_backtest_dataset,
)


BASE_TIME = datetime(2026, 5, 30, 18, 0, tzinfo=UTC)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        db_path = handle.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)
    Path(f"{db_path}-wal").unlink(missing_ok=True)
    Path(f"{db_path}-shm").unlink(missing_ok=True)


@pytest.fixture
def historian(temp_db: str) -> OddsHistorian:
    return OddsHistorian(db_path=temp_db)


def _register_match(
    historian: OddsHistorian,
    *,
    home_team: str = "Flamengo",
    away_team: str = "Palmeiras",
    league: str = "Brasileirao",
    scheduled_time: datetime = BASE_TIME,
) -> str:
    return historian.register_match(
        home_team=home_team,
        away_team=away_team,
        league=league,
        scheduled_time=scheduled_time,
    )


def _build_payload(
    base_time: datetime,
    *,
    invalid: bool = False,
) -> dict[str, dict[str, object]]:
    lag = 121 if invalid else 45
    return {
        "pinnacle": {
            "home": 2.10,
            "draw": 3.40,
            "away": 3.20,
            "captured_at": base_time,
        },
        "bet365": {
            "home": 2.05,
            "draw": 3.50,
            "away": 3.30,
            "captured_at": base_time + timedelta(seconds=30),
        },
        "betano": {
            "home": 2.20,
            "draw": 3.30,
            "away": 3.10,
            "captured_at": base_time + timedelta(seconds=lag),
        },
    }


def _store_snapshot(
    historian: OddsHistorian,
    match_id: str,
    captured_at: datetime,
    *,
    invalid: bool = False,
) -> int:
    return historian.store_snapshot(
        match_id=match_id,
        bookmaker_odds=_build_payload(captured_at, invalid=invalid),
        captured_at=captured_at + timedelta(seconds=121 if invalid else 45),
    )


def _set_finished_result(
    historian: OddsHistorian,
    match_id: str,
    *,
    home_goals: int = 2,
    away_goals: int = 1,
) -> None:
    historian.update_match_result(
        match_id=match_id,
        home_goals=home_goals,
        away_goals=away_goals,
    )


def _force_result_value(db_path: str, match_id: str, result: str | None) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE matches SET result = ? WHERE match_id = ?",
            (result, match_id),
        )
        connection.commit()
    finally:
        connection.close()


def test_returns_empty_list_when_database_has_no_data(historian: OddsHistorian) -> None:
    assert get_backtest_dataset(historian.db_path) == []


def test_returns_finished_match_with_valid_snapshot(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    snapshot_id = _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))
    _set_finished_result(historian, match_id)

    results = get_backtest_dataset(historian.db_path)

    assert len(results) == 1
    item = results[0]
    assert item.match_id == match_id
    assert item.home_team == "Flamengo"
    assert item.away_team == "Palmeiras"
    assert item.league == "Brasileirao"
    assert item.scheduled_time == BASE_TIME
    assert item.home_goals == 2
    assert item.away_goals == 1
    assert item.actual_result == "home_win"
    assert item.snapshot_id == snapshot_id
    assert item.valid_for_analysis is True


def test_does_not_return_match_without_real_result(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))

    assert get_backtest_dataset(historian.db_path) == []


def test_valid_only_true_excludes_invalid_snapshot(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5), invalid=True)
    _set_finished_result(historian, match_id)

    assert get_backtest_dataset(historian.db_path, valid_only=True) == []


def test_valid_only_false_returns_invalid_snapshot(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    snapshot_id = _store_snapshot(
        historian,
        match_id,
        BASE_TIME - timedelta(minutes=5),
        invalid=True,
    )
    _set_finished_result(historian, match_id)

    results = get_backtest_dataset(historian.db_path, valid_only=False)

    assert len(results) == 1
    assert results[0].snapshot_id == snapshot_id
    assert results[0].valid_for_analysis is False


def test_league_filter_returns_only_requested_league(historian: OddsHistorian) -> None:
    brasileirao_match = _register_match(historian, league="Brasileirao")
    premier_match = _register_match(
        historian,
        home_team="Arsenal",
        away_team="Liverpool",
        league="Premier League",
        scheduled_time=BASE_TIME + timedelta(hours=1),
    )
    _store_snapshot(historian, brasileirao_match, BASE_TIME - timedelta(minutes=10))
    _store_snapshot(historian, premier_match, BASE_TIME - timedelta(minutes=8))
    _set_finished_result(historian, brasileirao_match)
    _set_finished_result(historian, premier_match, home_goals=1, away_goals=1)

    results = get_backtest_dataset(historian.db_path, league="Premier League")

    assert [item.match_id for item in results] == [premier_match]
    assert results[0].league == "Premier League"


def test_limit_returns_deterministic_prefix(historian: OddsHistorian) -> None:
    first_match = _register_match(historian, home_team="A", away_team="B")
    second_match = _register_match(
        historian,
        home_team="C",
        away_team="D",
        scheduled_time=BASE_TIME + timedelta(hours=1),
    )
    _store_snapshot(historian, first_match, BASE_TIME - timedelta(minutes=10))
    _store_snapshot(historian, second_match, BASE_TIME - timedelta(minutes=8))
    _set_finished_result(historian, first_match)
    _set_finished_result(historian, second_match, home_goals=0, away_goals=1)

    results = get_backtest_dataset(historian.db_path, limit=1)

    assert [item.match_id for item in results] == [first_match]


@pytest.mark.parametrize("limit", (0, -1))
def test_limit_must_be_positive(historian: OddsHistorian, limit: int) -> None:
    with pytest.raises(ValueError, match="limit must be > 0"):
        get_backtest_dataset(historian.db_path, limit=limit)


@pytest.mark.parametrize(
    ("home_goals", "away_goals", "expected_result"),
    (
        (2, 1, "home_win"),
        (1, 1, "draw"),
        (0, 2, "away_win"),
    ),
)
def test_actual_result_can_be_calculated_from_goals(
    historian: OddsHistorian,
    home_goals: int,
    away_goals: int,
    expected_result: str,
) -> None:
    match_id = _register_match(
        historian,
        home_team=f"Home {home_goals}",
        away_team=f"Away {away_goals}",
    )
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))
    _set_finished_result(
        historian,
        match_id,
        home_goals=home_goals,
        away_goals=away_goals,
    )
    _force_result_value(historian.db_path, match_id, None)

    results = get_backtest_dataset(historian.db_path)

    assert results[0].actual_result == expected_result


def test_inconsistent_stored_result_fails_clearly(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))
    _set_finished_result(historian, match_id, home_goals=2, away_goals=1)
    _force_result_value(historian.db_path, match_id, "away_win")

    with pytest.raises(ValueError, match="stored result does not match scoreline"):
        get_backtest_dataset(historian.db_path)


def test_odds_payload_is_returned(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))
    _set_finished_result(historian, match_id)

    item = get_backtest_dataset(historian.db_path)[0]

    assert item.odds["pinnacle"] == {"home": 2.10, "draw": 3.40, "away": 3.20}
    assert item.odds["bet365"] == {"home": 2.05, "draw": 3.50, "away": 3.30}
    assert item.odds["betano"] == {"home": 2.20, "draw": 3.30, "away": 3.10}
    assert item.to_dict()["odds"] == item.odds


def test_security_flags_are_preserved(historian: OddsHistorian) -> None:
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, BASE_TIME - timedelta(minutes=5))
    _set_finished_result(historian, match_id)

    item = get_backtest_dataset(historian.db_path)[0]
    payload = item.to_dict()

    assert item.is_simulated is True
    assert item.paper_trading is True
    assert item.actionable is False
    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["actionable"] is False


def test_dataset_contract_has_no_position_sizing_fields() -> None:
    field_names = {field.name.lower() for field in fields(BacktestHistoricalMatch)}

    assert not any("sta" + "ke" in field_name for field_name in field_names)
    assert not any("kel" + "ly" in field_name for field_name in field_names)
    assert not any("bank" + "roll" in field_name for field_name in field_names)


def test_dataset_module_does_not_call_detector_or_model() -> None:
    source = inspect.getsource(dataset_module)

    assert "ValueDetector" not in source
    assert "value_detector" not in source
    assert "PoissonModel" not in source
    assert "poisson_model" not in source


def test_dataset_module_does_not_use_network_message_or_timing_services() -> None:
    source = inspect.getsource(dataset_module).lower()

    for forbidden in (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
    ):
        assert forbidden not in source


def test_dataset_module_does_not_implement_real_betting_or_financial_execution() -> None:
    source = inspect.getsource(dataset_module).lower()

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
    ):
        assert forbidden not in source
