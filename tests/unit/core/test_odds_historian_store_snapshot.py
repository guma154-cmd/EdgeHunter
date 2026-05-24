"""Tests for STORY-01-004 snapshot persistence and sync validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import json
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


def _build_payload(base_time: datetime) -> dict[str, dict[str, object]]:
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
            "captured_at": base_time + timedelta(seconds=45),
        },
    }


def _fetch_snapshot_row(db_path: str, snapshot_id: int) -> sqlite3.Row:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM odds_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        assert row is not None
        return row
    finally:
        connection.close()


def test_valid_snapshot_is_persisted(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)

    snapshot_id = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=_build_payload(base_time),
        captured_at=base_time + timedelta(seconds=45),
    )

    row = _fetch_snapshot_row(historian.db_path, snapshot_id)
    assert snapshot_id == row["id"]
    assert row["match_id"] == registered_match_id
    assert row["max_latency_seconds"] == 45
    assert row["valid_for_analysis"] == 1


def test_match_id_must_exist(
    historian: OddsHistorian,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="match_id does not exist"):
        historian.store_snapshot(
            match_id="missing-match",
            bookmaker_odds=_build_payload(base_time),
            captured_at=base_time,
        )


def test_odd_below_range_fails(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["pinnacle"]["home"] = 1.0

    with pytest.raises(ValueError, match="between 1.01 and 100.0"):
        historian.store_snapshot(
            match_id=registered_match_id,
            bookmaker_odds=payload,
            captured_at=base_time,
        )


def test_odd_above_range_fails(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["bet365"]["away"] = 100.5

    with pytest.raises(ValueError, match="between 1.01 and 100.0"):
        historian.store_snapshot(
            match_id=registered_match_id,
            bookmaker_odds=payload,
            captured_at=base_time,
        )


def test_non_numeric_odd_fails(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["betano"]["draw"] = "3.30"

    with pytest.raises(ValueError, match="must be numeric"):
        historian.store_snapshot(
            match_id=registered_match_id,
            bookmaker_odds=payload,
            captured_at=base_time,
        )


def test_naive_bookmaker_timestamp_fails(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["bet365"]["captured_at"] = datetime(2026, 5, 24, 17, 59, 30)

    with pytest.raises(ValueError, match="bet365.captured_at must be timezone-aware"):
        historian.store_snapshot(
            match_id=registered_match_id,
            bookmaker_odds=payload,
            captured_at=base_time,
        )


def test_naive_snapshot_captured_at_fails(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="captured_at must be timezone-aware"):
        historian.store_snapshot(
            match_id=registered_match_id,
            bookmaker_odds=_build_payload(base_time),
            captured_at=datetime(2026, 5, 24, 17, 59, 45),
        )


def test_latency_exactly_120_seconds_stays_valid(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["betano"]["captured_at"] = base_time + timedelta(seconds=120)

    snapshot_id = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=payload,
        captured_at=base_time + timedelta(seconds=120),
    )

    row = _fetch_snapshot_row(historian.db_path, snapshot_id)
    assert row["max_latency_seconds"] == 120
    assert row["valid_for_analysis"] == 1


def test_latency_above_120_seconds_persists_but_is_invalid(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["betano"]["captured_at"] = base_time + timedelta(seconds=121)

    snapshot_id = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=payload,
        captured_at=base_time + timedelta(seconds=121),
    )

    row = _fetch_snapshot_row(historian.db_path, snapshot_id)
    assert row["max_latency_seconds"] == 121
    assert row["valid_for_analysis"] == 0


def test_bookmakers_synced_is_calculated_and_persisted(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)
    payload["oddsportal_avg"] = {
        "home": 2.15,
        "draw": 3.45,
        "away": 3.15,
        "captured_at": base_time + timedelta(seconds=60),
    }

    snapshot_id = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=payload,
        captured_at=base_time + timedelta(seconds=60),
    )

    row = _fetch_snapshot_row(historian.db_path, snapshot_id)
    assert json.loads(row["bookmakers_synced"]) == [
        "bet365",
        "betano",
        "oddsportal_avg",
        "pinnacle",
    ]


def test_store_snapshot_is_not_idempotent_by_contract(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    base_time = datetime(2026, 5, 24, 17, 59, 0, tzinfo=UTC)
    payload = _build_payload(base_time)

    first = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=payload,
        captured_at=base_time + timedelta(seconds=45),
    )
    second = historian.store_snapshot(
        match_id=registered_match_id,
        bookmaker_odds=payload,
        captured_at=base_time + timedelta(seconds=45),
    )

    assert second != first
