"""Tests for STORY-01-007 scraper health evaluation."""

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


def _snapshot_payload(
    *,
    pinnacle_time: datetime | None = None,
    bet365_time: datetime | None = None,
    betano_time: datetime | None = None,
    oddsportal_time: datetime | None = None,
    pinnacle_home: float = 2.10,
    oddsportal_home: float = 2.12,
) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}
    if pinnacle_time is not None:
        payload["pinnacle"] = {
            "home": pinnacle_home,
            "draw": 3.40,
            "away": 3.20,
            "captured_at": pinnacle_time,
        }
    if bet365_time is not None:
        payload["bet365"] = {
            "home": 2.05,
            "draw": 3.50,
            "away": 3.30,
            "captured_at": bet365_time,
        }
    if betano_time is not None:
        payload["betano"] = {
            "home": 2.20,
            "draw": 3.30,
            "away": 3.10,
            "captured_at": betano_time,
        }
    if oddsportal_time is not None:
        payload["oddsportal_avg"] = {
            "home": oddsportal_home,
            "draw": 3.45,
            "away": 3.15,
            "captured_at": oddsportal_time,
        }
    return payload


def _persist_snapshot(
    historian: OddsHistorian,
    match_id: str,
    payload: dict[str, dict[str, object]],
    captured_at: datetime,
) -> None:
    historian.store_snapshot(
        match_id=match_id,
        bookmaker_odds=payload,
        captured_at=captured_at,
    )


def _health_by_name(results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["scraper_name"]): item for item in results}


def _fetch_latest_health_row(db_path: str, scraper_name: str) -> sqlite3.Row:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT *
            FROM scraper_health
            WHERE scraper_name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (scraper_name,),
        ).fetchone()
        assert row is not None
        return row
    finally:
        connection.close()


def test_scraper_with_recent_data_is_healthy(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    payload = _snapshot_payload(
        pinnacle_time=now - timedelta(minutes=5),
        bet365_time=now - timedelta(minutes=5),
        betano_time=now - timedelta(minutes=5),
        oddsportal_time=now - timedelta(minutes=5),
    )
    _persist_snapshot(historian, registered_match_id, payload, now - timedelta(minutes=5))

    results = _health_by_name(historian.evaluate_scraper_health(now=now))

    assert results["pinnacle"]["status"] == "healthy"
    assert results["bet365"]["status"] == "healthy"
    assert results["betano"]["status"] == "healthy"
    assert results["oddsportal"]["status"] == "healthy"


def test_scraper_without_data_for_two_cycles_is_warning(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            bet365_time=now - timedelta(minutes=30),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    results = _health_by_name(historian.evaluate_scraper_health(now=now))

    assert results["bet365"]["status"] == "warning"
    assert "no_data_recent_cycles" in results["bet365"]["issues"]
    assert results["bet365"]["alert_recommended"] is False


def test_scraper_with_stale_odds_is_critical(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=61),
            bet365_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    results = _health_by_name(historian.evaluate_scraper_health(now=now))

    assert results["pinnacle"]["status"] == "critical"
    assert "odds_stale" in results["pinnacle"]["issues"]
    assert results["pinnacle"]["alert_recommended"] is True


def test_complete_absence_of_recent_snapshots_is_critical(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            bet365_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    results = _health_by_name(historian.evaluate_scraper_health(now=now))

    assert results["oddsportal"]["status"] == "critical"
    assert "no_recent_snapshots" in results["oddsportal"]["issues"]


def test_divergence_above_threshold_is_detected(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            bet365_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
            pinnacle_home=2.10,
            oddsportal_home=2.50,
        ),
        now - timedelta(minutes=5),
    )

    results = _health_by_name(
        historian.evaluate_scraper_health(
            now=now,
            divergence_threshold_percent=10.0,
        )
    )

    assert results["pinnacle"]["status"] == "critical"
    assert results["pinnacle"]["divergence_detected"] is True
    assert results["oddsportal"]["divergence_detected"] is True
    assert "divergence_detected" in results["pinnacle"]["issues"]


def test_result_is_persisted_in_scraper_health(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            bet365_time=now - timedelta(minutes=30),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    historian.evaluate_scraper_health(now=now)
    row = _fetch_latest_health_row(historian.db_path, "bet365")

    assert row["status"] == "warning"
    assert row["consecutive_failures"] >= 2
    assert row["odds_stale"] == 0
    assert row["divergence_detected"] == 0


def test_alert_signal_is_decoupled_from_transaction(
    historian: OddsHistorian,
    registered_match_id: str,
) -> None:
    now = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)
    _persist_snapshot(
        historian,
        registered_match_id,
        _snapshot_payload(
            pinnacle_time=now - timedelta(minutes=61),
            bet365_time=now - timedelta(minutes=5),
            betano_time=now - timedelta(minutes=5),
            oddsportal_time=now - timedelta(minutes=5),
        ),
        now - timedelta(minutes=5),
    )

    results = _health_by_name(historian.evaluate_scraper_health(now=now))

    assert results["pinnacle"]["alert_recommended"] is True
    row = _fetch_latest_health_row(historian.db_path, "pinnacle")
    assert row["last_alert_sent"] is None
