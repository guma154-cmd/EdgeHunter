"""OddsHistorian foundation for schema bootstrap and match registration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
import json
import re
import sqlite3
from typing import Any

from .decorators import SHORT_TX
from .match_id import canonical_match_key, generate_match_id
from ..database.schema import configure_connection, ensure_schema


MIN_ODD = 1.01
MAX_ODD = 100.0
SYNC_TOLERANCE_SECONDS = 120
SUPPORTED_BOOKMAKERS: tuple[str, ...] = (
    "pinnacle",
    "bet365",
    "betano",
    "oddsportal_avg",
)


class OddsHistorian:
    """Bootstrap the SQLite schema and register matches idempotently."""

    def __init__(self, db_path: str = "edge_hunter.db") -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if not ensure_schema(self.db_path):
            raise RuntimeError(f"failed to initialize OddsHistorian schema at {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        configure_connection(connection)
        return connection

    @staticmethod
    def _validate_required_text(value: str, field_name: str) -> str:
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty")
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _ensure_aware_datetime(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @staticmethod
    def _validate_match_exists(connection: sqlite3.Connection, match_id: str) -> None:
        row = connection.execute(
            "SELECT 1 FROM matches WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"match_id does not exist: {match_id}")

    def _validate_snapshot_payload(
        self,
        match_id: str,
        bookmaker_odds: dict[str, dict[str, Any]],
        captured_at: datetime,
    ) -> dict[str, Any]:
        match_id_clean = self._validate_required_text(match_id, "match_id")
        snapshot_captured_at = self._ensure_aware_datetime(captured_at, "captured_at")

        if not bookmaker_odds:
            raise ValueError("bookmaker_odds cannot be empty")

        normalized_bookmakers: dict[str, dict[str, Any]] = {}
        bookmaker_timestamps: list[datetime] = []

        for bookmaker_name, bookmaker_payload in bookmaker_odds.items():
            if bookmaker_name not in SUPPORTED_BOOKMAKERS:
                raise ValueError(f"unsupported bookmaker: {bookmaker_name}")
            if not isinstance(bookmaker_payload, dict):
                raise ValueError(f"{bookmaker_name} payload must be a dictionary")

            normalized_entry: dict[str, Any] = {}
            for outcome in ("home", "draw", "away"):
                odd_value = bookmaker_payload.get(outcome)
                if not isinstance(odd_value, (int, float)) or isinstance(odd_value, bool):
                    raise ValueError(f"{bookmaker_name}.{outcome} must be numeric")
                odd_value = float(odd_value)
                if odd_value < MIN_ODD or odd_value > MAX_ODD:
                    raise ValueError(
                        f"{bookmaker_name}.{outcome} must be between {MIN_ODD} and {MAX_ODD}"
                    )
                normalized_entry[outcome] = odd_value

            bookmaker_captured_at = self._ensure_aware_datetime(
                bookmaker_payload.get("captured_at"),
                f"{bookmaker_name}.captured_at",
            )
            bookmaker_timestamps.append(bookmaker_captured_at)
            normalized_entry["captured_at"] = bookmaker_captured_at
            normalized_bookmakers[bookmaker_name] = normalized_entry

        max_captured_at = max(bookmaker_timestamps)
        min_captured_at = min(bookmaker_timestamps)
        max_latency_seconds = int((max_captured_at - min_captured_at) / timedelta(seconds=1))
        bookmakers_synced = sorted(normalized_bookmakers)

        return {
            "match_id": match_id_clean,
            "snapshot_captured_at": snapshot_captured_at,
            "bookmakers": normalized_bookmakers,
            "bookmakers_synced": bookmakers_synced,
            "bookmakers_synced_json": json.dumps(bookmakers_synced),
            "max_latency_seconds": max_latency_seconds,
            "valid_for_analysis": max_latency_seconds <= SYNC_TOLERANCE_SECONDS,
        }

    @SHORT_TX(max_duration_ms=100)
    def register_match(
        self,
        home_team: str,
        away_team: str,
        league: str,
        scheduled_time: datetime,
        source: str | None = None,
        external_id: str | None = None,
    ) -> str:
        del source, external_id
        home_team_clean = self._validate_required_text(home_team, "home_team")
        away_team_clean = self._validate_required_text(away_team, "away_team")
        league_clean = self._validate_required_text(league, "league")

        match_id = generate_match_id(
            home_team=home_team_clean,
            away_team=away_team_clean,
            league=league_clean,
            scheduled_time=scheduled_time,
        )
        normalized_time = scheduled_time.astimezone(timezone.utc).replace(microsecond=0)
        expected_key = canonical_match_key(
            home_team=home_team_clean,
            away_team=away_team_clean,
            league=league_clean,
            scheduled_time=normalized_time,
        )

        connection = self._connect()
        try:
            cursor = connection.execute(
                """
                SELECT home_team, away_team, league, match_date
                FROM matches
                WHERE match_id = ?
                """,
                (match_id,),
            )
            row = cursor.fetchone()
            if row is not None:
                existing_key = canonical_match_key(
                    home_team=row[0],
                    away_team=row[1],
                    league=row[2],
                    scheduled_time=datetime.fromisoformat(row[3]),
                )
                if existing_key != expected_key:
                    raise ValueError(
                        "match_id collision detected for a different match payload"
                    )
                return match_id

            connection.execute(
                """
                INSERT INTO matches (
                    match_id,
                    home_team,
                    away_team,
                    league,
                    match_date
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    home_team_clean,
                    away_team_clean,
                    league_clean,
                    normalized_time.isoformat(timespec="seconds"),
                ),
            )
            connection.commit()
            return match_id
        finally:
            connection.close()

    @SHORT_TX(max_duration_ms=100)
    def store_snapshot(
        self,
        match_id: str,
        bookmaker_odds: dict[str, dict[str, Any]],
        captured_at: datetime,
        source: str | None = None,
    ) -> int:
        del source

        payload = self._validate_snapshot_payload(
            match_id=match_id,
            bookmaker_odds=bookmaker_odds,
            captured_at=captured_at,
        )

        validation_connection = self._connect()
        try:
            self._validate_match_exists(validation_connection, payload["match_id"])
        finally:
            validation_connection.close()

        bookmakers = payload["bookmakers"]
        write_connection = self._connect()
        try:
            cursor = write_connection.execute(
                """
                INSERT INTO odds_snapshots (
                    match_id,
                    pinnacle_home,
                    pinnacle_draw,
                    pinnacle_away,
                    pinnacle_timestamp,
                    bet365_home,
                    bet365_draw,
                    bet365_away,
                    bet365_timestamp,
                    betano_home,
                    betano_draw,
                    betano_away,
                    betano_timestamp,
                    oddsportal_avg_home,
                    oddsportal_avg_draw,
                    oddsportal_avg_away,
                    oddsportal_timestamp,
                    max_latency_seconds,
                    bookmakers_synced,
                    valid_for_analysis,
                    snapshot_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["match_id"],
                    bookmakers.get("pinnacle", {}).get("home"),
                    bookmakers.get("pinnacle", {}).get("draw"),
                    bookmakers.get("pinnacle", {}).get("away"),
                    (
                        bookmakers.get("pinnacle", {}).get("captured_at").isoformat(
                            timespec="seconds"
                        )
                        if "pinnacle" in bookmakers
                        else None
                    ),
                    bookmakers.get("bet365", {}).get("home"),
                    bookmakers.get("bet365", {}).get("draw"),
                    bookmakers.get("bet365", {}).get("away"),
                    (
                        bookmakers.get("bet365", {}).get("captured_at").isoformat(
                            timespec="seconds"
                        )
                        if "bet365" in bookmakers
                        else None
                    ),
                    bookmakers.get("betano", {}).get("home"),
                    bookmakers.get("betano", {}).get("draw"),
                    bookmakers.get("betano", {}).get("away"),
                    (
                        bookmakers.get("betano", {}).get("captured_at").isoformat(
                            timespec="seconds"
                        )
                        if "betano" in bookmakers
                        else None
                    ),
                    bookmakers.get("oddsportal_avg", {}).get("home"),
                    bookmakers.get("oddsportal_avg", {}).get("draw"),
                    bookmakers.get("oddsportal_avg", {}).get("away"),
                    (
                        bookmakers.get("oddsportal_avg", {}).get("captured_at").isoformat(
                            timespec="seconds"
                        )
                        if "oddsportal_avg" in bookmakers
                        else None
                    ),
                    payload["max_latency_seconds"],
                    payload["bookmakers_synced_json"],
                    int(payload["valid_for_analysis"]),
                    payload["snapshot_captured_at"].isoformat(timespec="seconds"),
                ),
            )
            write_connection.commit()
            return int(cursor.lastrowid)
        finally:
            write_connection.close()
