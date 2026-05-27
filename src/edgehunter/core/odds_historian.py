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
DEFAULT_SCRAPER_CYCLE_MINUTES = 15
SUPPORTED_BOOKMAKERS: tuple[str, ...] = (
    "pinnacle",
    "bet365",
    "betano",
    "oddsportal_avg",
)
SCRAPER_COLUMN_MAP: dict[str, str] = {
    "pinnacle": "pinnacle",
    "bet365": "bet365",
    "betano": "betano",
    "oddsportal": "oddsportal_avg",
}
SCRAPER_NAMES: tuple[str, ...] = tuple(SCRAPER_COLUMN_MAP)


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

    @staticmethod
    def _parse_optional_timestamp(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    @staticmethod
    def _validate_non_negative_goal_count(value: int, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{field_name} must be >= 0")
        return value

    @staticmethod
    def _compute_match_result(home_goals: int, away_goals: int) -> str:
        if home_goals > away_goals:
            return "home_win"
        if home_goals < away_goals:
            return "away_win"
        return "draw"

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

    @SHORT_TX(max_duration_ms=100)
    def update_match_result(
        self,
        match_id: str,
        home_goals: int,
        away_goals: int,
    ) -> None:
        match_id_clean = self._validate_required_text(match_id, "match_id")
        home_goals_clean = self._validate_non_negative_goal_count(home_goals, "home_goals")
        away_goals_clean = self._validate_non_negative_goal_count(away_goals, "away_goals")
        result = self._compute_match_result(home_goals_clean, away_goals_clean)

        connection = self._connect()
        try:
            self._validate_match_exists(connection, match_id_clean)
            connection.execute(
                """
                UPDATE matches
                SET
                    home_goals = ?,
                    away_goals = ?,
                    result = ?,
                    status = 'finished',
                    updated_at = CURRENT_TIMESTAMP
                WHERE match_id = ?
                """,
                (
                    home_goals_clean,
                    away_goals_clean,
                    result,
                    match_id_clean,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def get_finished_matches_with_last_odds(
        self,
        valid_only: bool = True,
    ) -> list[dict[str, Any]]:
        valid_clause = "AND s.valid_for_analysis = 1" if valid_only else ""
        connection = self._connect()
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                f"""
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.league,
                    m.match_date,
                    m.home_goals,
                    m.away_goals,
                    m.result,
                    s.id AS snapshot_id,
                    s.pinnacle_home,
                    s.pinnacle_draw,
                    s.pinnacle_away,
                    s.bet365_home,
                    s.bet365_draw,
                    s.bet365_away,
                    s.betano_home,
                    s.betano_draw,
                    s.betano_away,
                    s.oddsportal_avg_home,
                    s.oddsportal_avg_draw,
                    s.oddsportal_avg_away,
                    s.bookmakers_synced,
                    s.valid_for_analysis,
                    s.snapshot_timestamp,
                    s.max_latency_seconds
                FROM matches AS m
                JOIN odds_snapshots AS s
                    ON s.id = (
                        SELECT s2.id
                        FROM odds_snapshots AS s2
                        WHERE
                            s2.match_id = m.match_id
                            {valid_clause}
                        ORDER BY s2.snapshot_timestamp DESC, s2.id DESC
                        LIMIT 1
                    )
                WHERE
                    m.status = 'finished'
                    AND m.home_goals IS NOT NULL
                    AND m.away_goals IS NOT NULL
                    AND m.result IS NOT NULL
                ORDER BY m.match_date ASC, m.match_id ASC
                """
            ).fetchall()
        finally:
            connection.close()

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "match_id": row["match_id"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "league": row["league"],
                    "scheduled_time": datetime.fromisoformat(row["match_date"]),
                    "home_goals": int(row["home_goals"]),
                    "away_goals": int(row["away_goals"]),
                    "result": row["result"],
                    "snapshot_id": int(row["snapshot_id"]),
                    "pinnacle_home": row["pinnacle_home"],
                    "pinnacle_draw": row["pinnacle_draw"],
                    "pinnacle_away": row["pinnacle_away"],
                    "bet365_home": row["bet365_home"],
                    "bet365_draw": row["bet365_draw"],
                    "bet365_away": row["bet365_away"],
                    "betano_home": row["betano_home"],
                    "betano_draw": row["betano_draw"],
                    "betano_away": row["betano_away"],
                    "oddsportal_avg_home": row["oddsportal_avg_home"],
                    "oddsportal_avg_draw": row["oddsportal_avg_draw"],
                    "oddsportal_avg_away": row["oddsportal_avg_away"],
                    "bookmakers_synced": json.loads(row["bookmakers_synced"]),
                    "valid_for_analysis": bool(row["valid_for_analysis"]),
                    "last_snapshot_at": datetime.fromisoformat(row["snapshot_timestamp"]),
                    "max_latency_seconds": row["max_latency_seconds"],
                }
            )
        return results

    @staticmethod
    def _build_snapshot_odds_payload(row: sqlite3.Row) -> dict[str, dict[str, float]]:
        odds: dict[str, dict[str, float]] = {}
        for bookmaker in SUPPORTED_BOOKMAKERS:
            home = row[f"{bookmaker}_home"]
            draw = row[f"{bookmaker}_draw"]
            away = row[f"{bookmaker}_away"]
            if home is None or draw is None or away is None:
                continue
            odds[bookmaker] = {
                "home": float(home),
                "draw": float(draw),
                "away": float(away),
            }
        return odds

    def get_recent_valid_snapshots(
        self,
        minutes: int = 30,
        league: str | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if minutes <= 0:
            raise ValueError("minutes must be > 0")

        reference_time = (
            datetime.now(UTC).replace(microsecond=0)
            if now is None
            else self._ensure_aware_datetime(now, "now")
        )
        window_start = reference_time - timedelta(minutes=minutes)

        league_clause = ""
        params: list[Any] = [
            window_start.isoformat(timespec="seconds"),
            reference_time.isoformat(timespec="seconds"),
        ]
        if league is not None:
            league_clause = "AND m.league = ?"
            params.append(self._validate_required_text(league, "league"))

        connection = self._connect()
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                f"""
                SELECT
                    s.id AS snapshot_id,
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.league,
                    m.match_date,
                    s.pinnacle_home,
                    s.pinnacle_draw,
                    s.pinnacle_away,
                    s.bet365_home,
                    s.bet365_draw,
                    s.bet365_away,
                    s.betano_home,
                    s.betano_draw,
                    s.betano_away,
                    s.oddsportal_avg_home,
                    s.oddsportal_avg_draw,
                    s.oddsportal_avg_away,
                    s.bookmakers_synced,
                    s.valid_for_analysis,
                    s.snapshot_timestamp,
                    s.max_latency_seconds
                FROM odds_snapshots AS s
                JOIN matches AS m
                    ON m.match_id = s.match_id
                WHERE
                    s.valid_for_analysis = 1
                    AND s.snapshot_timestamp >= ?
                    AND s.snapshot_timestamp <= ?
                    {league_clause}
                ORDER BY s.snapshot_timestamp DESC, s.id DESC
                """,
                tuple(params),
            ).fetchall()
        finally:
            connection.close()

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "snapshot_id": int(row["snapshot_id"]),
                    "match_id": row["match_id"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "league": row["league"],
                    "scheduled_time": datetime.fromisoformat(row["match_date"]),
                    "snapshot_timestamp": datetime.fromisoformat(row["snapshot_timestamp"]),
                    "bookmakers_synced": json.loads(row["bookmakers_synced"]),
                    "valid_for_analysis": bool(row["valid_for_analysis"]),
                    "max_latency_seconds": row["max_latency_seconds"],
                    "odds": self._build_snapshot_odds_payload(row),
                }
            )
        return results

    def _read_latest_scraper_timestamps(
        self,
        now: datetime,
    ) -> dict[str, datetime | None]:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT
                    MAX(pinnacle_timestamp) AS pinnacle_timestamp,
                    MAX(bet365_timestamp) AS bet365_timestamp,
                    MAX(betano_timestamp) AS betano_timestamp,
                    MAX(oddsportal_timestamp) AS oddsportal_timestamp
                FROM odds_snapshots
                WHERE snapshot_timestamp <= ?
                """,
                (now.isoformat(timespec="seconds"),),
            ).fetchone()
            assert row is not None
            return {
                "pinnacle": self._parse_optional_timestamp(row[0]),
                "bet365": self._parse_optional_timestamp(row[1]),
                "betano": self._parse_optional_timestamp(row[2]),
                "oddsportal": self._parse_optional_timestamp(row[3]),
            }
        finally:
            connection.close()

    def _read_divergence_flags(
        self,
        now: datetime,
        divergence_threshold_percent: float,
    ) -> dict[str, bool]:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT
                    pinnacle_home,
                    pinnacle_draw,
                    pinnacle_away,
                    oddsportal_avg_home,
                    oddsportal_avg_draw,
                    oddsportal_avg_away
                FROM odds_snapshots
                WHERE
                    snapshot_timestamp <= ?
                    AND pinnacle_timestamp IS NOT NULL
                    AND oddsportal_timestamp IS NOT NULL
                ORDER BY snapshot_timestamp DESC
                LIMIT 1
                """,
                (now.isoformat(timespec="seconds"),),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return {scraper_name: False for scraper_name in SCRAPER_NAMES}

        divergence_detected = False
        pairs = (
            (float(row[0]), float(row[3])),
            (float(row[1]), float(row[4])),
            (float(row[2]), float(row[5])),
        )
        for left_value, right_value in pairs:
            smaller = min(left_value, right_value)
            if smaller <= 0:
                continue
            diff_percent = abs(left_value - right_value) / smaller * 100.0
            if diff_percent > divergence_threshold_percent:
                divergence_detected = True
                break

        flags = {scraper_name: False for scraper_name in SCRAPER_NAMES}
        if divergence_detected:
            flags["pinnacle"] = True
            flags["oddsportal"] = True
        return flags

    @staticmethod
    def _build_health_result(
        scraper_name: str,
        checked_at: datetime,
        last_data_collected: datetime | None,
        consecutive_failures: int,
        odds_stale: bool,
        divergence_detected: bool,
        no_data_warning_cycles: int,
    ) -> dict[str, Any]:
        issues: list[str] = []
        status = "healthy"

        if last_data_collected is None:
            issues.append("no_recent_snapshots")
            status = "critical"
        elif divergence_detected:
            issues.append("divergence_detected")
            status = "critical"
        elif odds_stale:
            issues.append("odds_stale")
            status = "critical"
        elif consecutive_failures >= no_data_warning_cycles:
            issues.append("no_data_recent_cycles")
            status = "warning"

        return {
            "scraper_name": scraper_name,
            "status": status,
            "last_successful_run": last_data_collected,
            "last_data_collected": last_data_collected,
            "consecutive_failures": consecutive_failures,
            "odds_stale": odds_stale,
            "divergence_detected": divergence_detected,
            "checked_at": checked_at,
            "issues": issues,
            "alert_recommended": status == "critical",
        }

    @SHORT_TX(max_duration_ms=100)
    def _persist_scraper_health_records(
        self,
        health_records: list[dict[str, Any]],
    ) -> None:
        connection = self._connect()
        try:
            for record in health_records:
                connection.execute(
                    """
                    INSERT INTO scraper_health (
                        scraper_name,
                        last_successful_run,
                        last_data_collected,
                        consecutive_failures,
                        odds_stale,
                        divergence_detected,
                        status,
                        last_alert_sent,
                        checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["scraper_name"],
                        (
                            record["last_successful_run"].isoformat(timespec="seconds")
                            if record["last_successful_run"] is not None
                            else None
                        ),
                        (
                            record["last_data_collected"].isoformat(timespec="seconds")
                            if record["last_data_collected"] is not None
                            else None
                        ),
                        record["consecutive_failures"],
                        int(record["odds_stale"]),
                        int(record["divergence_detected"]),
                        record["status"],
                        None,
                        record["checked_at"].isoformat(timespec="seconds"),
                    ),
                )
            connection.commit()
        finally:
            connection.close()

    def evaluate_scraper_health(
        self,
        now: datetime,
        stale_after_minutes: int = 60,
        no_data_warning_cycles: int = 2,
        divergence_threshold_percent: float = 10.0,
    ) -> list[dict[str, Any]]:
        checked_at = self._ensure_aware_datetime(now, "now")
        latest_timestamps = self._read_latest_scraper_timestamps(checked_at)
        divergence_flags = self._read_divergence_flags(
            checked_at,
            divergence_threshold_percent,
        )

        health_records: list[dict[str, Any]] = []
        for scraper_name in SCRAPER_NAMES:
            last_data_collected = latest_timestamps[scraper_name]
            consecutive_failures = no_data_warning_cycles + 1
            odds_stale = False

            if last_data_collected is not None:
                age_minutes = (checked_at - last_data_collected).total_seconds() / 60.0
                consecutive_failures = int(age_minutes // DEFAULT_SCRAPER_CYCLE_MINUTES)
                odds_stale = age_minutes > stale_after_minutes

            health_records.append(
                self._build_health_result(
                    scraper_name=scraper_name,
                    checked_at=checked_at,
                    last_data_collected=last_data_collected,
                    consecutive_failures=consecutive_failures,
                    odds_stale=odds_stale,
                    divergence_detected=divergence_flags[scraper_name],
                    no_data_warning_cycles=no_data_warning_cycles,
                )
            )

        self._persist_scraper_health_records(health_records)
        return health_records
