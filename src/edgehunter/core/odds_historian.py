"""OddsHistorian foundation for schema bootstrap and match registration."""

from __future__ import annotations

from datetime import datetime, timezone
import re
import sqlite3

from .decorators import SHORT_TX
from .match_id import canonical_match_key, generate_match_id
from ..database.schema import configure_connection, ensure_schema


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
