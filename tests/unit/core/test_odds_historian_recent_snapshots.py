"""Tests for STORY-03-SUP-002 recent valid snapshot queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import inspect
import tempfile

import pytest

from src.edgehunter.core import odds_historian as odds_historian_module
from src.edgehunter.core.odds_historian import OddsHistorian


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
    scheduled_time: datetime = datetime(2026, 5, 27, 21, 0, tzinfo=UTC),
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


def test_returns_recent_valid_snapshot(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    match_id = _register_match(historian)
    snapshot_id = _store_snapshot(historian, match_id, now - timedelta(minutes=10))

    results = historian.get_recent_valid_snapshots(minutes=30, now=now)

    assert len(results) == 1
    assert results[0]["snapshot_id"] == snapshot_id
    assert results[0]["match_id"] == match_id
    assert results[0]["valid_for_analysis"] is True


def test_does_not_return_invalid_snapshot(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, now - timedelta(minutes=10), invalid=True)

    results = historian.get_recent_valid_snapshots(minutes=30, now=now)

    assert results == []


def test_does_not_return_snapshot_outside_time_window(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    match_id = _register_match(historian)
    _store_snapshot(historian, match_id, now - timedelta(minutes=31))

    results = historian.get_recent_valid_snapshots(minutes=30, now=now)

    assert results == []


def test_league_filter_returns_only_requested_league(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    brasileirao_match = _register_match(historian, league="Brasileirao")
    premier_match = _register_match(
        historian,
        home_team="Arsenal",
        away_team="Liverpool",
        league="Premier League",
    )
    _store_snapshot(historian, brasileirao_match, now - timedelta(minutes=10))
    _store_snapshot(historian, premier_match, now - timedelta(minutes=8))

    results = historian.get_recent_valid_snapshots(
        minutes=30,
        league="Premier League",
        now=now,
    )

    assert [item["match_id"] for item in results] == [premier_match]
    assert results[0]["league"] == "Premier League"


def test_without_league_filter_returns_multiple_leagues(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    brasileirao_match = _register_match(historian, league="Brasileirao")
    premier_match = _register_match(
        historian,
        home_team="Arsenal",
        away_team="Liverpool",
        league="Premier League",
    )
    _store_snapshot(historian, brasileirao_match, now - timedelta(minutes=10))
    _store_snapshot(historian, premier_match, now - timedelta(minutes=8))

    results = historian.get_recent_valid_snapshots(minutes=30, now=now)

    assert {item["league"] for item in results} == {"Brasileirao", "Premier League"}


def test_orders_from_newest_to_oldest(historian: OddsHistorian) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    old_match = _register_match(historian, home_team="A", away_team="B")
    new_match = _register_match(historian, home_team="C", away_team="D")
    old_snapshot = _store_snapshot(historian, old_match, now - timedelta(minutes=20))
    new_snapshot = _store_snapshot(historian, new_match, now - timedelta(minutes=5))

    results = historian.get_recent_valid_snapshots(minutes=30, now=now)

    assert [item["snapshot_id"] for item in results] == [new_snapshot, old_snapshot]


@pytest.mark.parametrize("minutes", (0, -1))
def test_minutes_must_be_positive(historian: OddsHistorian, minutes: int) -> None:
    with pytest.raises(ValueError, match="minutes must be > 0"):
        historian.get_recent_valid_snapshots(minutes=minutes)


def test_naive_now_fails(historian: OddsHistorian) -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        historian.get_recent_valid_snapshots(
            minutes=30,
            now=datetime(2026, 5, 27, 18, 0),
        )


def test_returned_item_contains_minimum_match_snapshot_and_odds_fields(
    historian: OddsHistorian,
) -> None:
    now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
    match_id = _register_match(historian)
    snapshot_id = _store_snapshot(historian, match_id, now - timedelta(minutes=10))

    item = historian.get_recent_valid_snapshots(minutes=30, now=now)[0]

    assert item["snapshot_id"] == snapshot_id
    assert item["match_id"] == match_id
    assert item["home_team"] == "Flamengo"
    assert item["away_team"] == "Palmeiras"
    assert item["league"] == "Brasileirao"
    assert item["scheduled_time"] == datetime(2026, 5, 27, 21, 0, tzinfo=UTC)
    assert item["snapshot_timestamp"] == now - timedelta(minutes=10) + timedelta(seconds=45)
    assert item["bookmakers_synced"] == ["bet365", "betano", "pinnacle"]
    assert item["valid_for_analysis"] is True
    assert item["odds"]["pinnacle"] == {"home": 2.10, "draw": 3.40, "away": 3.20}
    assert item["odds"]["bet365"] == {"home": 2.05, "draw": 3.50, "away": 3.30}
    assert item["odds"]["betano"] == {"home": 2.20, "draw": 3.30, "away": 3.10}


def test_recent_snapshot_query_does_not_call_value_detector_or_poisson_model() -> None:
    source = inspect.getsource(odds_historian_module)

    assert "ValueDetector" not in source
    assert "value_detector" not in source
    assert "PoissonModel" not in source
    assert "poisson_model" not in source


def test_recent_snapshot_query_does_not_use_network_telegram_or_scheduler() -> None:
    source = inspect.getsource(odds_historian_module)

    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scheduler" not in source.lower()


def test_recent_snapshot_query_does_not_implement_betting_or_financial_execution() -> None:
    source = inspect.getsource(odds_historian_module).lower()

    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source
    assert "place_bet" not in source
    assert "real_money" not in source
