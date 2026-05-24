"""Tests for STORY-01-003 match registration."""

from __future__ import annotations

from datetime import UTC, datetime
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


def _count_matches(db_path: str) -> int:
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    finally:
        connection.close()


def _fetch_match_row(db_path: str, match_id: str) -> tuple[str, str, str, str, str]:
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            """
            SELECT match_id, home_team, away_team, league, match_date
            FROM matches
            WHERE match_id = ?
            """,
            (match_id,),
        ).fetchone()
        assert row is not None
        return row
    finally:
        connection.close()


def test_register_match_is_idempotent(temp_db: str) -> None:
    historian = OddsHistorian(db_path=temp_db)
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = historian.register_match(
        home_team="Flamengo FC",
        away_team="Palmeiras",
        league="Brasileirao",
        scheduled_time=scheduled_time,
    )
    second = historian.register_match(
        home_team="Flamengo FC",
        away_team="Palmeiras",
        league="Brasileirao",
        scheduled_time=scheduled_time,
    )

    assert first == second
    assert _count_matches(temp_db) == 1


def test_register_match_persists_normalized_inputs(temp_db: str) -> None:
    historian = OddsHistorian(db_path=temp_db)
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    match_id = historian.register_match(
        home_team="  São   Paulo FC ",
        away_team="PALMEIRAS",
        league="Brasileirão ",
        scheduled_time=scheduled_time,
        source="pinnacle",
        external_id="abc-123",
    )

    assert _fetch_match_row(temp_db, match_id) == (
        match_id,
        "São Paulo FC",
        "PALMEIRAS",
        "Brasileirão",
        "2026-05-24T18:00:00+00:00",
    )


def test_register_match_rejects_naive_datetime(temp_db: str) -> None:
    historian = OddsHistorian(db_path=temp_db)

    with pytest.raises(ValueError, match="timezone-aware"):
        historian.register_match(
            home_team="Flamengo",
            away_team="Palmeiras",
            league="Brasileirao",
            scheduled_time=datetime(2026, 5, 24, 18, 0),
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    (
        ("home_team", {"home_team": " ", "away_team": "Palmeiras", "league": "Brasileirao"}),
        ("away_team", {"home_team": "Flamengo", "away_team": "", "league": "Brasileirao"}),
        ("league", {"home_team": "Flamengo", "away_team": "Palmeiras", "league": " "}),
    ),
)
def test_register_match_rejects_empty_required_fields(
    temp_db: str,
    field_name: str,
    kwargs: dict[str, str],
) -> None:
    historian = OddsHistorian(db_path=temp_db)

    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        historian.register_match(
            scheduled_time=datetime(2026, 5, 24, 18, 0, tzinfo=UTC),
            **kwargs,
        )


def test_register_match_does_not_duplicate_equivalent_normalized_match(temp_db: str) -> None:
    historian = OddsHistorian(db_path=temp_db)
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = historian.register_match(
        home_team="São Paulo FC",
        away_team="Palmeiras",
        league="Brasileirão",
        scheduled_time=scheduled_time,
    )
    second = historian.register_match(
        home_team="s. paulo",
        away_team="palmeiras",
        league="brasileirao",
        scheduled_time=scheduled_time,
    )

    assert first == second
    assert _count_matches(temp_db) == 1
