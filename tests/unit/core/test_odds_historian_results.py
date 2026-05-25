"""Tests for result updates and finished-match queries used by PoissonModel prep."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile

import pytest

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


@pytest.fixture
def registered_match_id(historian: OddsHistorian) -> str:
    return historian.register_match(
        home_team="Flamengo",
        away_team="Palmeiras",
        league="Brasileirao",
        scheduled_time=datetime(2026, 5, 24, 18, 0, tzinfo=UTC),
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


def _fetch_match_result_row(db_path: str, match_id: str) -> sqlite3.Row:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT match_id, home_goals, away_goals, result, status
            FROM matches
            WHERE match_id = ?
            """,
            (match_id,),
        ).fetchone()
        assert row is not None
        return row
    finally:
        connection.close()


def test_update_match_result_updates_score_and_status(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=2,
        away_goals=1,
    )

    row = _fetch_match_result_row(historian.db_path, registered_match_id)
    assert row["home_goals"] == 2
    assert row["away_goals"] == 1
    assert row["result"] == "home_win"
    assert row["status"] == "finished"


def test_update_match_result_calculates_draw(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=1,
        away_goals=1,
    )

    row = _fetch_match_result_row(historian.db_path, registered_match_id)
    assert row["result"] == "draw"


def test_update_match_result_calculates_away_win(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=0,
        away_goals=3,
    )

    row = _fetch_match_result_row(historian.db_path, registered_match_id)
    assert row["result"] == "away_win"


def test_update_match_result_fails_for_missing_match_id(historian: OddsHistorian) -> None:
    with pytest.raises(ValueError, match="match_id does not exist"):
        historian.update_match_result(
            match_id="missing-match",
            home_goals=1,
            away_goals=0,
        )


@pytest.mark.parametrize("field_name", ("home_goals", "away_goals"))
def test_update_match_result_rejects_negative_goals(
    historian: OddsHistorian,
    registered_match_id: str,
    field_name: str,
) -> None:
    kwargs = {"home_goals": 1, "away_goals": 0}
    kwargs[field_name] = -1

    with pytest.raises(ValueError, match=f"{field_name} must be >= 0"):
        historian.update_match_result(match_id=registered_match_id, **kwargs)


@pytest.mark.parametrize("field_name", ("home_goals", "away_goals"))
def test_update_match_result_rejects_non_integer_goals(
    historian: OddsHistorian,
    registered_match_id: str,
    field_name: str,
) -> None:
    kwargs = {"home_goals": 1, "away_goals": 0}
    kwargs[field_name] = 1.5

    with pytest.raises(ValueError, match=f"{field_name} must be an integer"):
        historian.update_match_result(match_id=registered_match_id, **kwargs)


def test_get_finished_matches_with_last_odds_returns_valid_snapshot_only(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=_build_payload(base_time),
        captured_at=base_time + timedelta(seconds=45),
    )
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=2,
        away_goals=1,
    )

    results = historian.get_finished_matches_with_last_odds(valid_only=True)

    assert len(results) == 1
    assert results[0]["match_id"] == registered_match_id
    assert results[0]["result"] == "home_win"
    assert results[0]["valid_for_analysis"] is True
    assert results[0]["bookmakers_synced"] == ["bet365", "betano", "pinnacle"]


def test_valid_only_true_excludes_invalid_snapshot(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=_build_payload(base_time, invalid=True),
        captured_at=base_time + timedelta(seconds=121),
    )
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=1,
        away_goals=0,
    )

    results = historian.get_finished_matches_with_last_odds(valid_only=True)

    assert results == []


def test_valid_only_false_allows_invalid_snapshot(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=_build_payload(base_time, invalid=True),
        captured_at=base_time + timedelta(seconds=121),
    )
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=1,
        away_goals=0,
    )

    results = historian.get_finished_matches_with_last_odds(valid_only=False)

    assert len(results) == 1
    assert results[0]["valid_for_analysis"] is False


def test_finished_match_without_snapshot_is_excluded(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    historian.update_match_result(
        match_id=registered_match_id,
        home_goals=0,
        away_goals=0,
    )

    results = historian.get_finished_matches_with_last_odds(valid_only=True)

    assert results == []


def test_results_module_does_not_introduce_network_telegram_or_scraper_access() -> None:
    source = Path("src/edgehunter/core/odds_historian.py").read_text(encoding="utf-8")

    assert "requests" not in source
    assert "telegram" not in source.lower()
    assert "playwright" not in source.lower()
